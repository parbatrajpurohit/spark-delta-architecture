# METRICS DB

This project involves setting up a distributed data processing environment using Docker Compose. The system integrates Apache Spark, Hive, and PostgreSQL to manage and analyze large datasets efficiently. The Docker Compose configuration facilitates seamless communication and monitoring across various services:

- PostgreSQL serves as the backend database, providing storage for Hive Metastore metadata.
- pgAdmin4 offers a web-based interface to manage PostgreSQL databases.
- Spark includes both master and worker containers, enabling distributed data processing.
- Hive Metastore manages table metadata, crucial for Hive's data warehouse capabilities.
- An API service is available for Delta table management, supporting tasks such as data uploads and SQL query execution.

## Containers Overview

### PostgreSQL (postgres)
- Purpose: Serves as the backend database for Hive Metastore.
- Ports: `localhost:5432`

### pgAdmin4
- Purpose: Web interface to manage PostgreSQL.
- Ports: `localhost:9500`

### Spark Master (spark-master)
- Purpose: Manages the Spark cluster.
- Ports: `localhost:8080` (Web UI), `7077` (internal communication)

### Spark Worker 1 (spark-worker)
- Purpose: Executes Spark tasks.
- Ports: `localhost:8081`

### Spark Worker 2 (spark-worker2)
- Purpose: Executes Spark tasks.
- Ports: `localhost:8082`

### Hive Metastore (hive-metastore)
- Purpose: Manages metadata for Hive tables.
- Ports: `9083` (internal Thrift service)

## Resources Required for the Setup

Suggested resource allocation (can be scaled up):

```
1) spark-master    - 4 GB RAM, 2 cores
2) spark-connect   - 4 GB RAM, 2 cores
3) spark-worker    - 4 GB RAM, 2 cores
4) spark-worker2   - 4 GB RAM, 2 cores
```

## Setup Instructions

1. Change folder permissions (in WSL2):
```bash
sudo chmod -R 777 {relative_path}/Parbat_Project/delta-tables
```
Apply the same for:
- `delta-tables`
- `hive-placeholder`
- `query-results`
- `configs`

2. Start the Docker containers:
```bash
docker-compose up -d
```

3. Restart Hive Metastore (only needed on first run):
```bash
docker restart hive-metastore
```

## Project Execution

### Writing a Delta Table
1. Install dependencies
2. Run `api_endpoints` to start the API service
3. Provide file paths in `_create_delta_table.py`
4. Run the script to create and store Delta tables in the `delta-tables` folder

### Reading a Delta Table
1. Access pgAdmin (localhost:9500) and log in
2. Browse the `meta_data` database → `_meta_data_json_` table
3. Retrieve table names and versions based on queries
4. Use `client_request.py` to specify the table name and output file path
5. Execute and check the `query-results` folder for output

### Utility Scripts (Located in `test/` folder)
- `parquet_file_read.py`: Reads query result files
- `read_delta_table.py`: Reads Delta table content
- `read_delta_plaintext.py`: Reads Delta table as plain text

## Problems During Integration

### 1. PySpark 3.4.3 not working with Python 3.11
- **Fix**: Use Python 3.10

### 2. Spark-connect config write error
- **Fix**: Run `chmod 777 configs`

### 3. Spark-connect failed downloading extensions
- **Fix**: Ensure internet or provide offline packages

### 4. Delta table creation failed initially
- **Fix**: Restart the stack and try again

## Docker Build Issues

### 1. Permission denied during image build
- **Fix**: Use `DOCKER_BUILDKIT=0` when building

### 2. psycopg2 compile error (pg_config not found)
- **Fix**: Install system dependencies:
```bash
apt-get install python3-dev libpq-dev gcc
