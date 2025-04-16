# python standard library
import os
import random
import re
import shutil
import threading
import time

from contextlib import contextmanager
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import List
from typing import Optional

# 3rd party libraries
import psycopg2
import uvicorn
import pandas as pd

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pyspark.sql import SparkSession

from .spark_functions import create_delta_tables

# package imports



# Global logger initializations
logger = getLogger()

# Relative path to the project
TMP_DIR = Path(__file__).parent / '../tmp'

# Define base path for Delta tables
if Path('/mnt').exists():
    BASE_PATH = Path('/mnt/delta-tables')
else:
    BASE_PATH = Path(__file__).parent / '../delta-tables'

postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
spark_connect_host = os.getenv('SPARK_CONNECT_HOST', 'localhost')

# @todo remove from source code
DB_CONFIG = {
    "dbname": "Meta_data",
    "user": "MetricsDB",
    "password": "password",
    "host": postgres_host,
    "port": "5432"
}

# Initialize Spark session with Delta Lake support
def create_spark_session():
    spark = SparkSession.builder \
        .appName("MetricsDB") \
        .remote(f"sc://{spark_connect_host}:15002") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.sql.warehouse.dir", "/opt/bitnami/spark/spark-warehouse") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .config("spark.sql.execution.metrics.enabled", "false") \
        .config("spark.kryoserializer.buffer.max", "512m") \
        .config("spark.rpc.message.maxSize", "512") \
        .enableHiveSupport() \
        .getOrCreate()
    return spark


# Global Spark session
spark = create_spark_session()


class MetaData(BaseModel):
    evaluation_identifier: str


class FileList(BaseModel):
    filepaths: List[str]


class SQLQueryRequest(BaseModel):
    table_name: str
    sql_query: str

class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass


class Api:
    __version__ = '0.2.2dev'

    def __init__(self, port: int = 8123):

        git_commit_hash = os.getenv('GIT_COMMIT', None)

        version = self.__version__
        if git_commit_hash is not None:
            version += f"_{git_commit_hash}"

        self.app = FastAPI(
            title="MetricsDB",
            description="MetricsDB API provides different endpoints for pushing metrics to and to query data from delta tables 🚀",
            summary="API to push and query parquet files and metadata using HTTP",
            version=version,
            contact={
                "name": "Andreas Hanauska",
                "url": "https://github-vni.geo.conti.de/HanauskaA",
                "email": "andreas.hanauska@continental.com",
            },
            license_info={
                "name": "Proprietary License (only to be used in Continental AG)",
            }
        )
        self.setup_routes()

        templates_dir = Path(__file__).parent / "templates"
        staticfiles_dir = Path(__file__).parent / "images"

        self.templates = Jinja2Templates(directory=templates_dir)
        self.app.mount("/images", StaticFiles(directory=staticfiles_dir), name="images")

        self.port = port
        self.config = uvicorn.Config(
            self.app,
            port=self.port,
            log_level="info",
        )
        self.server = Server(config=self.config)
        self.server_thread = threading.Thread(target=self.server.run)

    def setup_routes(self):
        # only for local developments
        # self.app.add_api_route(
        #     "/run-sql/",
        #     self.run_sql_query,
        #     methods=["POST"]
        # )

        self.app.add_api_route(
            "/upload/",
            self.process_files,
            methods=["POST"]
        )

        # self.app.add_api_route(
        #     "/read-delta/",
        #     self.read_delta_table,
        #     methods=["GET"]
        # )

        self.app.add_api_route(
            "/table/data/",
            self.get_data,
            methods=["GET", "POST"],  # https://github.com/fastapi/fastapi/issues/4740
        )

        self.app.add_api_route(
            "/table/info/",
            self.get_tables_dep,
            methods=["GET"],
            response_model=dict
        )

        self.app.add_api_route(
            "/table/versions/",
            self.get_versions_for_table,
            methods=["GET"],
        )

        self.app.add_api_route(
            "/metadata/view/",
            self.view_metadata,
            methods=["GET"],
            response_class=HTMLResponse,
        )

        self.app.add_api_route(
            "/metadata/search/",
            self.search_table_names,
            methods=["GET"],
        )

        self.app.add_api_route(
            "/metadata/table/",
            self.get_metadata_for_table_version,
            methods=["GET"],
        )

    def start(self):
        self.server_thread.start()

    def shutdown(self):
        logger.info(f"Waiting for '{self.server_thread.name}' to terminate gracefully.")
        self.server.should_exit = True
        self.server_thread.join()

    @staticmethod
    def remove_temporary_files(directories: List[Path]) -> None:
        for directory in directories:
            shutil.rmtree(directory)

    @staticmethod
    def get_columns_for_table(table_name):
        """
        Load the table schema and return a list of all column names wrapped in backticks for SQL query.
        """
        try:
            # Load the Delta table into Spark DataFrame to get the schema
            table_path = BASE_PATH / table_name.strip()
            table_path = table_path.as_posix()

            df = spark.read.format("delta").load(table_path)
            columns = [f"`{col}`" for col in df.columns]  # Escape column names with backticks
            return columns
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error loading table schema: {str(e)}")


    @staticmethod
    def validate_sql_query(query: str):
        # Allowed SQL Query types (only SELECT)
        # Regular expression to check for only SELECT queries
        pattern = r'^\s*SELECT\b'

        # Forbidden keywords: DELETE, INSERT, UPDATE, etc.
        forbidden_keywords = ["DELETE", "INSERT", "UPDATE", "DROP", "ALTER", "TRUNCATE"]

        # Check if the query starts with "SELECT"
        if not re.match(pattern, query, re.IGNORECASE):
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed.")

        # Check for forbidden keywords in the query
        if any(re.search(rf'\b{kw}\b', query, re.IGNORECASE) for kw in forbidden_keywords):
            raise HTTPException(status_code=400,
                                detail=f"The query contains forbidden operations: {forbidden_keywords}")

        return True


    def run_sql_query(self, request: SQLQueryRequest):
        """
        Runs a dynamic SQL query on the Delta table and saves the result as a Parquet file.
        Handles `SELECT *` queries by dynamically replacing it with the list of all column names.
        """
        try:
            # @todo add a test: This should not be required any more when using a temporary view.
            #   But the table name is not guaranteed to be the only, so it is difficult to compile to a final version.
            #   A workaround shall be found.
            # Check if it's a SELECT * query, replace it with all escaped columns
            if "SELECT *" in request.sql_query.upper():
                # Retrieve the escaped column names for the table
                escaped_columns = self.get_columns_for_table(request.table_name)
                column_list = ", ".join(escaped_columns)
                # Replace 'SELECT *' with the full column list
                request.sql_query = request.sql_query.replace("*", column_list)

            # Log the final SQL query for debug
            logger.info(f"Executing SQL query: {request.sql_query}")

            # Validate the SQL query
            self.validate_sql_query(request.sql_query)

            # Load the Delta table into a Spark view
            delta_table_path = BASE_PATH / request.table_name.strip()
            delta_table_path = delta_table_path.as_posix()

            df = spark.read.format("delta").load(delta_table_path)
            df.createOrReplaceTempView("delta_table")

            # Execute the SQL query
            result = spark.sql(request.sql_query).collect()

            # Convert the result into a Pandas DataFrame
            pd_df = pd.DataFrame([row.asDict() for row in result])

            # Define a temporary directory to store the Parquet file
            output_path = TMP_DIR  # Temporary directory

            # Ensure the output directory exists
            output_path.mkdir(parents=True, exist_ok=True)

            # Define the file name for the Parquet file
            parquet_file_path = output_path / "query_result.parquet"

            # Write the Pandas DataFrame to Parquet
            pd_df.to_parquet(parquet_file_path, index=False, engine="pyarrow", compression="gzip", coerce_timestamps='us', store_schema=False)
            # compression = "gzip",
            # engine = "pyarrow",
            # coerce_timestamps = 'us',
            # store_schema = False

            # Ensure the file was written correctly
            if not parquet_file_path.exists():
                raise HTTPException(status_code=500, detail="Failed to generate Parquet file")

            logger.info(f"Parquet file successfully saved at: {parquet_file_path}")

            # Return the Parquet file as a download response
            return FileResponse(str(parquet_file_path), media_type="application/octet-stream",
                                filename="query_result.parquet")

        except Exception as e:
            logger.exception(f"Error running SQL query: {e}")
            raise HTTPException(status_code=500, detail=f"Error running SQL query: {str(e)}")

    def process_files(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),  # List of Parquet files
        metadata_file: Optional[UploadFile] = File(None)  # Optional JSON metadata file
    ):
        try:
            # Navigate to the project root (go up from app directory if needed)
            base_dir = Path(__file__).resolve().parent.parent  # Move up one directory from the script folder
            temp_path = base_dir / "tmp" / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            temp_path.mkdir(parents=True, exist_ok=True)  # Create the directories if they don't exist
        except Exception as e:
            logger.exception(f"Could not create temporary directory: {e}")
            raise HTTPException(status_code=500, detail="Failed to create temporary directory")

        else:
            try:
                filenames = [f.filename for f in files]
                assert len(filenames) == len(set(filenames)), "Filenames should be unique"

                for file in files:
                    logger.info(f"Processing {file.filename}")

                    # Copy the file to a local directory
                    target_file = temp_path / file.filename
                    with open(target_file, 'wb') as f:
                        shutil.copyfileobj(file.file, f)

                    # Call the create_or_append_delta_table function
                    create_delta_tables(spark, target_file, metadata_file, credentials=DB_CONFIG)  # Pass the metadata file to the function

            except Exception as e:
                logger.exception(f"Error processing files: {e}")
                raise HTTPException(status_code=500, detail="Failed to process files")

            finally:
                # Cleanup temporary files after background tasks are done
                background_tasks.add_task(shutil.rmtree, temp_path)

            return "Files processed successfully"

    def read_delta_table(self, table_name: str, limit: int = 100000000):
        """
        Reads the Delta table from the provided table name and returns the data in tabular format.
        This endpoint only allows SELECT operations (no modification queries).
        """
        try:
            # Construct the full table path based on the user-provided table name
            delta_table_path = BASE_PATH / table_name.strip('`')
            delta_table_path = delta_table_path.as_posix()  # Convert to POSIX-style path

            logger.info(f"Attempting to read Delta table from: {delta_table_path}")  # Log the path

            # Read the Delta table directly
            df = spark.read.format("delta").load(delta_table_path)

            # Limit the result based on the provided limit parameter
            result_df = df.limit(limit).toPandas()

            # Convert the result DataFrame to a tabular string format
            result_string = result_df.to_string(index=False)

            # Return the result as plain text
            return PlainTextResponse(result_string)

        except Exception as e:
            # Handle exceptions and return an error message
            logger.exception(f"Error reading Delta table: {e}")
            raise HTTPException(status_code=500, detail=f"Error reading Delta table: {str(e)}")

    def get_tables_dep(self, task_id: str) -> dict:
        """
        Endpoint to retrieve the table name and available versions for a specific task ID by searching metadata.
        """
        try:
            # Connect to the PostgresSQL database
            with psycopg2.connect(**DB_CONFIG) as conn:
                with conn.cursor() as cur:
                    # Query to find matching table names for the given task ID
                    cur.execute(
                        """
                        SELECT delta_table_name, version
                        FROM meta_data_json
                        WHERE metadata ->> 'Task_ID' = %s
                        ORDER BY delta_table_name, version ASC
                        """, (task_id,))

                    rows = cur.fetchall()

                    # If no matching tables are found, return an error
                    if not rows:
                        raise HTTPException(
                            status_code=404,
                            detail=f"No matching tables found for the provided task ID: {task_id}"
                        )

                    # Create a dictionary to hold table names and their versions
                    tables_info = {}
                    for row in rows:
                        table_name, version = row
                        if table_name not in tables_info:
                            tables_info[table_name] = []
                        tables_info[table_name].append(version)

                    # Return the table names and available versions
                    return {
                        "tables": tables_info
                    }

        except Exception as e:
            # Handle exceptions and return an error message
            error_message = f"Error retrieving table information: {e}"
            logger.exception(error_message)
            raise HTTPException(status_code=500, detail=error_message)


    def get_data(
        self,
        background_tasks: BackgroundTasks,
        table_name: str,
        version: Optional[int] = None
    ):
        # Ensure Unix-style path
        delta_table_path = Path(BASE_PATH, table_name).as_posix()
        logger.info(f"Attempting to load Delta Table from: {delta_table_path} with version: {version}")

        # Define a temporary path for saving the Parquet file
        task_id = f"get_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}-{random.randint(1000, 2000)}"
        output_dir = TMP_DIR / task_id
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Load the Delta Table with Spark, considering the specified version
            if version is not None:
                df = spark.read.format("delta").option("versionAsOf", version).load(delta_table_path)
            else:
                df = spark.read.format("delta").load(delta_table_path)

            # Using the temporary view 'delta_table' can be used to work around the select * problematic
            # (which doesn't seem to work on spark dataframes by default)
            df.createOrReplaceTempView("delta_table")

            # Execute the SQL query
            result = spark.sql(f"SELECT * FROM delta_table").collect()

            # Convert the result into a Pandas DataFrame
            pd_df = pd.DataFrame([row.asDict() for row in result])

            # Convert the Spark DataFrame to a Pandas DataFrame directly
            # pd_df = df.toPandas()

            # Define a temporary path for saving the Parquet file
            parquet_file_path = output_dir / f"{table_name}_data.parquet"

            # Write the DataFrame to Parquet format
            pd_df.to_parquet(parquet_file_path, index=False, engine="pyarrow", compression="gzip")

            # Return the Parquet file as a downloadable response
            return FileResponse(
                path=str(parquet_file_path),
                media_type="application/octet-stream",
                filename=f"{table_name}_data.parquet"
            )

        except Exception as e:
            # Refine the error message to avoid serialization of non-serializable objects
            error_message = f"Error retrieving data from {table_name} (version {version}): {str(e)}"
            logger.exception(error_message)
            raise HTTPException(status_code=500, detail=error_message)
        finally:
            background_tasks.add_task(self.remove_temporary_files, [output_dir])

    def view_metadata(self, request: Request):
        """
        Serve the metadata_search.html template for viewing and interacting with metadata.
        """
        return self.templates.TemplateResponse("metadata_search.html", {"request": request})

    def search_table_names(self, query: str):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()

            sql = """
                SELECT DISTINCT delta_table_name
                FROM meta_data_json
                {where}
                ORDER BY delta_table_name
            """

            if query:
                where=f"WHERE delta_table_name ILIKE %s"
            else:
                where = ""

            sql = sql.format(where=where)

            cur.execute(sql, (f"%{query}%",))

            rows = cur.fetchall()
            matching_tables = [row[0] for row in rows]

            logger.info(matching_tables)

            cur.close()
            conn.close()

            return JSONResponse(content=matching_tables)

        except Exception as e:
            error_message = f"Error retrieving table names: {e}"
            logger.exception(error_message)
            raise HTTPException(status_code=500, detail=error_message)


    def get_versions_for_table(self, table_name: str):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT version
                FROM meta_data_json
                WHERE delta_table_name = %s
                ORDER BY version DESC
            """, (table_name,))

            rows = cur.fetchall()
            versions = [row[0] for row in rows]

            cur.close()
            conn.close()

            return JSONResponse(content=versions)

        except Exception as e:
            error_message = f"Error retrieving versions: {e}"
            logger.exception(error_message)
            raise HTTPException(status_code=500, detail=error_message)


    def get_metadata_for_table_version(self, table_name: str, version: int):
        """ New endpoint to fetch metadata for a specific table and version """
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("""
                SELECT metadata
                FROM meta_data_json
                WHERE delta_table_name = %s AND version = %s
            """, (table_name, version))

            row = cur.fetchone()

            if not row:
                return JSONResponse(
                    content={"detail": "No data found for the specified table and version"},
                    status_code=404
                )

            metadata = row[0]

            cur.close()
            conn.close()

            return JSONResponse(content=metadata)

        except Exception as e:
            error_message = f"Error retrieving metadata: {e}"
            logger.exception(error_message)
            raise HTTPException(status_code=500, detail=error_message)


@contextmanager
def api_server(port: int):
    api = Api(port)
    api.start()
    # wait until the server is up and running
    while api.server.started is False:
        time.sleep(0.1)
    try:
        yield api
    finally:
        api.shutdown()