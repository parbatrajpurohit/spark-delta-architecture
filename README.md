# METRICS DB

This project involves setting up a distributed data processing environment using Docker Compose. The system integrates Apache Spark, Hive, and PostgreSQL to manage and analyze large datasets efficiently. The Docker Compose configuration facilitates seamless communication and monitoring across various services:

PostgreSQL serves as the backend database, providing storage for Hive Metastore metadata.
pgAdmin4 offers a web-based interface to manage PostgreSQL databases.
Spark includes both master and worker containers, enabling distributed data processing.
Hive Metastore manages table metadata, crucial for Hive's data warehouse capabilities.
This setup leverages specific ports for each service, ensuring smooth operation and interconnectivity. Additionally, an API service is available for Delta table management, supporting tasks such as data uploads and SQL query execution.

## Containers Overview

### PostgreSQL (postgres)

Purpose: Serves as the backend database for Hive Metastore, storing metadata for Hive tables.

**Ports**:

- Accessible on localhost:5432 for database connections.

### pgAdmin4

Purpose: Provides a web-based graphical interface to manage the PostgreSQL database. This is useful for visual database management and running SQL queries.

**Ports**:

- Accessible on localhost:9500.

### Spark Master (spark-master)

Purpose: Manages the Spark cluster, orchestrates tasks, and provides a web UI for monitoring the Spark environment.

**Ports**:

- 8080: Web UI for Spark Master accessible on localhost:8080.
- 7077: Port for internal communication within the Spark cluster, accessed by Spark workers and clients.

### Spark Worker 1 (spark-worker)

Purpose: A worker node that executes tasks as directed by the Spark Master. It contributes to distributed processing.

**Ports**:

- 8081: Web UI for monitoring Spark Worker 1, accessible on localhost:8081.

### Spark Worker 2 (spark-worker2)

Purpose: Another worker node for distributed processing, similar to Spark Worker 1, providing additional computational resources.

**Ports**:

- 8082: Web UI for monitoring Spark Worker 2, accessible on localhost:8082.

### Hive Metastore (hive-metastore)

Purpose: Manages metadata for Hive tables, facilitating data warehousing capabilities by allowing queries to access table schemas.

**Ports**:

- 9083: The Hive Metastore Thrift service, which allows other services to connect, although not directly accessible on localhost as it’s primarily for internal use.



## Resources Required for the Setup

It can be increased as per the need.

1) spark-master	4 GB (Driver)	2 cores (Driver)
2) spark-connect	4 GB (Driver)	2 cores (Driver)
3) spark-worker	4 GB (Executor)	2 cores
4) spark-worker2	4 GB (Executor)	2 cores

## Setup Instructions 

There are some folder which might need the read and write permissions without that it will not be possible to create the delta tables.
We can change the folder permission from the WSL command line prompt for if these are the folders. 

**delta-tables, hive-placeholder, query-results, configs**


```bash
sudo chmod -R 777 {relative_path}/Parbat_Project/delta-tables
```
Similarly, we can change the permission for other folders too.


Since the containers are already set up in the project, you can start the Docker stack on the WSL2 machine by running the following command:
```bash
docker-compose up -d
```

After the container images are downloaded, all containers will start, except for hive-metastore. On the first run, hive-metastore will stop as it requires PostgreSQL as a backend for schema initialization.

To fix this, simply restart the hive-metastore container using the following command:
```bash
docker restart hive-metastore
```

Once everything is running, confirm the setup by checking the hive-metastore folder. This folder should contain PostgreSQL files.
![img_1.png](images%2Fimg_1.png)
**_Project Execution:_**
**Writing a Delta-tables**

Step 1: Install all necessary dependencies on the system.

Step 2: Start the api_endpoints program to activate all API endpoints.
![img_2.png](images%2Fimg_2.png)
Step 3: Choose the required files: i) Parquet file, and ii) Meta_data file. Enter their paths in the test file, _create_delta_table.py.


Step 4: Run the program. Once the Delta table is created, it will be visible in the delta-tables folder, and you can monitor all stages via the Spark Connect web UI on Port 4040.
![img_3.png](images%2Fimg_3.png)

**Reading a Delta Table**

Step 1: To read Delta tables, identify the desired table and the specific data required. You can access this information through the pgAdmin interface, available on Port 9500, where you can view a list of all tables along with their version numbers and associated metadata.

After logging into pgAdmin, enter the credentials, select the Meta_data database, and choose the table _meta_data_json_. Here, you’ll find a list of tables along with their versions. You can query the table to retrieve the names of all tables that meet the query criteria.

**_Query_**
![img_4.png](images%2Fimg_4.png)
_**Query_result**_
![img_5.png](images%2Fimg_5.png)

Step2: Once you have the table names, you can query specific tables by using the test script. Specify the table name and the data you need. Use _client_request.py_ to set the output path for the query result file, where you want to save the output.

![img_7.png](images%2Fimg_7.png)

Step3: Once run the file he can see the result file in the query result folder.

![img_6.png](images%2Fimg_6.png)

At the end we read the file using pandas or any other Libraries.

Some scripts are available in the test folder that can be used for reading Parquet files or accessing Delta tables directly:

1) parquet_file_read.py: Used to read the query results.
2) read_delta_table.py: Reads data from the Delta table.
3) read_delta_plaintext.py: Reads the content of the table as plain text.
4) read_delta_table.py: Displays the table's content, version number, and history.

# Problems during the integration test

1. Could not install pyspark==3.4.3 using python 3.11, python 3.10 was required to be able to build the wheel locally
2. The spark connect container crashed with the error message: "/opt/bitnami/scripts/spark/entrypoint.sh: line 30: /opt/bitnami/spark/conf/spark-env.sh: Permission denied"

    Symptom: The create table query failed:

        ´´´python
        INFO:     127.0.0.1:52774 - "POST /upload HTTP/1.1" 307 Temporary Redirect
        Processing 20241014_075113_Pinching Evaluation.parquet
        Metadata loaded: {'Task_ID': '1', 'Algorithm_Name': 'test', 'Algorithm_Version': '0.0.1'}
        Error creating Delta table or interacting with PostgreSQL: <_MultiThreadedRendezvous of RPC that terminated with:
            status = StatusCode.UNAVAILABLE
            details = "failed to connect to all addresses; last error: UNAVAILABLE: ipv4:127.0.0.1:15002: ConnectEx: Connection refused (No connection could be made because the target machine actively refused it.
         -- 10061)"
            debug_error_string = "UNKNOWN:Error received from peer  {grpc_message:"failed to connect to all addresses; last error: UNAVAILABLE: ipv4:127.0.0.1:15002: ConnectEx: Connection refused (No connection could be made because the target machine actively refused it.\r\n -- 10061)", grpc_status:14, created_time:"2024-10-22T12:01:51.1971435+00:00"}"
        ´´´
      
     **Reason**: When starting the spark-connect container, writing to the config directory did not work:

      ``` bash
      if [ ! $EUID -eq 0 ] && [ -e "$LIBNSS_WRAPPER_PATH" ]; then
        echo "spark:x:$(id -u):$(id -g):Spark:$SPARK_HOME:/bin/false" > "$NSS_WRAPPER_PASSWD"
        echo "spark:x:$(id -g):" > "$NSS_WRAPPER_GROUP"
        # line 30: 
        echo "LD_PRELOAD=$LIBNSS_WRAPPER_PATH" >> "$SPARK_CONF_DIR/spark-env.sh"
      fi
      ```
     Solution: chmod 777 configs

3. Same error message as in 2. but the reason is that the spark-connect container cannot download the required extension 
   packages.

   Somehow it work some days later, but we should have a solution which is independent of a working internet connection
   to be more stable.

4. An initial run of `create_delta_table` initially caused an error which indicated that the delta storage package was not available/working properly.
   After restarting the stack with the original configuration the error could not be reproduced.

## Docker Build

1. Issue when building the docker image: ERROR: failed to solve: error from sender: open hive-metastore: permission denied

   Reason: https://stackoverflow.com/a/78959568/1504082

   "You're probably suffering from docker/cli #3043: all files in the build context directory are read, no matter if 
   they are excluded in the .dockerignore file. Unfortunately the issue was closed without a fix. docker/buildx #1781 
   is related and pending without a solution at the time of writing (09/2024)."

   Solution: Use DOCKER_BUILDKIT=0 in the build command

2. psycopg2 cannot be compiled when the docker image gets build.

   Reason: pg_config executable not found

   Solution: See https://stackoverflow.com/a/64604562/1504082: Add python3-dev libpq-dev gcc to the apt-get install
   call to fix the