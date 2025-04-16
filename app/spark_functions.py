from pyspark.sql import SparkSession
import pyarrow.parquet as pq
import re
import json
import psycopg2


def create_delta_table_name(metadata):
    """Generate the Delta table name based on the metadata."""
    task_id = re.sub(r'[^a-zA-Z0-9_]', '_', metadata.get("Task_ID"))
    algorithm_name = re.sub(r'[^a-zA-Z0-9_]', '_', metadata.get("Algorithm_Name"))
    algorithm_version = re.sub(r'[^a-zA-Z0-9_]', '_', metadata.get("Algorithm_Version").replace("v", ""))

    # Format the table name based on the provided format, ensuring it's SQL safe
    table_name = f"{task_id}_{algorithm_name}_v{algorithm_version}"
    return table_name


def create_delta_tables(spark, parquet_file, metadata_file, credentials):
    try:
        # Load metadata from JSON file
        new_metadata = json.load(metadata_file.file)
        print("Metadata loaded:", new_metadata)

        # Generate the table name based on metadata
        delta_table_name = create_delta_table_name(new_metadata)
        delta_table_path = f"/opt/bitnami/spark/spark-warehouse/{delta_table_name}"

        # Reading the Parquet file and creating a Delta table in Spark
        parquet_file_path = parquet_file
        table = pq.read_table(parquet_file_path)
        df = table.to_pandas()

        # Convert pandas DataFrame to Spark DataFrame
        spark_df = spark.createDataFrame(df)

        # Add user metadata as part of the write operation to Delta table
        user_metadata = json.dumps(new_metadata)  # Convert the metadata dict to a JSON string

        # Check if the table exists using `tableExists()`
        if not spark.catalog.tableExists(f"default.{delta_table_name}"):
            # If the table does not exist, create it
            print(f"Creating a new Delta table: {delta_table_name}")
            spark_df.write.format("delta") \
                .option("mergeSchema", "true") \
                .option("path", delta_table_path) \
                .option("userMetadata", user_metadata) \
                .option("delta.columnMapping.mode", "name") \
                .option("delta.minReaderVersion", "2") \
                .option("delta.minWriterVersion", "5") \
                .mode("overwrite") \
                .saveAsTable(delta_table_name)

            # Register the external table in Hive Metastore if needed
            spark.sql(f"""
                CREATE TABLE IF NOT EXISTS {delta_table_name}
                USING DELTA
                LOCATION '{delta_table_path}';
            """)
        else:
            # If the table exists, append the data
            print(f"Table {delta_table_name} exists. Appending data to the Delta table.")
            spark_df.write.format("delta") \
                .option("mergeSchema", "true") \
                .mode("append") \
                .option("delta.columnMapping.mode", "name") \
                .option("userMetadata", user_metadata) \
                .option("delta.minReaderVersion", "2") \
                .option("delta.minWriterVersion", "5") \
                .save(delta_table_path)

        # Handle metadata in PostgreSQL for versioning
        conn = psycopg2.connect(**credentials)
        print("Connected to PostgreSQL successfully.")
        cur = conn.cursor()

        # Create a PostgreSQL table for storing metadata if it doesn't already exist
        create_table_query = """
            CREATE TABLE IF NOT EXISTS Meta_data_json (
                id SERIAL PRIMARY KEY,
                delta_table_name VARCHAR(255),
                metadata JSONB,
                version INT DEFAULT 0,  -- Set default to 0
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        cur.execute(create_table_query)
        conn.commit()

        # Check if metadata for this Delta table already exists
        cur.execute("""
            SELECT id, metadata::TEXT, version FROM Meta_data_json
            WHERE delta_table_name = %s
            ORDER BY version DESC LIMIT 1;
        """, (delta_table_name,))

        existing_row = cur.fetchone()

        if existing_row:
            # Metadata already exists, compare it with the new metadata
            existing_id, existing_metadata_json, existing_version = existing_row
            existing_metadata = json.loads(existing_metadata_json)

            new_version = existing_version + 1  # Increment the existing version
            insert_query = """
                INSERT INTO Meta_data_json (delta_table_name, metadata, version)
                VALUES (%s, %s, %s);
            """
            cur.execute(insert_query, (
                delta_table_name,
                json.dumps(new_metadata),
                new_version
            ))
            #print(f"Metadata for {delta_table_name} updated to version {new_version} in PostgreSQL.")
            print(f"{delta_table_name} updated to version {new_version} in PostgreSQL.")
            if existing_metadata != new_metadata:
                print(f"Metadata for {delta_table_name} changed.")
        else:
            # Metadata does not exist, insert a new row with version 0
            insert_query = """
                INSERT INTO Meta_data_json (delta_table_name, metadata, version)
                VALUES (%s, %s, 0);
            """
            cur.execute(insert_query, (
                delta_table_name,
                json.dumps(new_metadata)
            ))
            print(f"Metadata for {delta_table_name} inserted as version 0 in PostgreSQL.")

        conn.commit()
        cur.close()
        conn.close()

        print(f"Delta table '{delta_table_name}' created and metadata registered successfully in PostgreSQL.")

    except Exception as e:
        print(f"Error creating Delta table or interacting with PostgreSQL: {e}")
        import traceback
        traceback.print_exc()