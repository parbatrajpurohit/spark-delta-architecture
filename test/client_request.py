from http import HTTPStatus
from logging import getLogger
import requests
import os
from datetime import datetime
from functools import wraps
from time import time


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print('func:%r took: %2.4f sec' % (f.__name__, te - ts))
        # print('func:%r args:[%r, %r] took: %2.4f sec' % (f.__name__, args, kw, te-ts))
        return result
    return wrap


logger = getLogger()
LOCAL_PORT = 5001
BASE_URL = f'http://127.0.0.1:{LOCAL_PORT}'

# User Input
TABLE_NAME = "DEP_2657_Antipinch_v6_0"

# SQL query you want to execute on the Delta table
SQL_QUERY = f"""
    SELECT * 
    FROM {TABLE_NAME}
    VERSION AS OF 99
"""

# Specify where to save the Parquet file
OUTPUT_PATH = r"F:\Parbat_Project\query-results"


@timing
def run_sql_query_and_get_parquet():
    url = f'{BASE_URL}/run-sql/'

    # Prepare the request payload
    payload = {
        "table_name": TABLE_NAME,
        "sql_query": SQL_QUERY,
        "output_path": OUTPUT_PATH
    }

    # Send the POST request
    logger.info(f"Sending SQL query to: {url}")
    resp = requests.post(url, json=payload)

    # Check if the request was successful
    if resp.status_code == HTTPStatus.OK:
        # Generate a valid timestamp string for the filename
        current_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(OUTPUT_PATH, f"query_result_{current_timestamp}.parquet")

        # Write the binary content directly to a file
        with open(filename, 'wb') as f:
            f.write(resp.content)  # Ensure the file is saved as binary data
        print(f"Parquet file saved successfully at: {filename}")

    else:
        print(f"Failed to run SQL query. Status code: {resp.status_code}, Response: {resp.text}")


if __name__ == '__main__':
    run_sql_query_and_get_parquet()
