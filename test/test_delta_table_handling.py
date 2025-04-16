# python standard library
from datetime import datetime
from http import HTTPStatus
from logging import getLogger
from pathlib import Path

# 3rd party libraries
import requests
import pytest

# package imports
from test import timing

base_path = Path(__file__).parent

logger = getLogger()

TEST_FILE = base_path / 'data/20241014_075113_Pinching Evaluation.parquet'
METADATA_FILE = base_path / 'data/20241014_075113_Pinching Evaluation.metadata.json'

TMP_DIR = base_path / 'tmp'
TMP_DIR.mkdir(exist_ok=True)


@timing
def test_file_upload(api_connection, base_url):
    url = f'{base_url}/upload'

    files = [
        ('files', open(TEST_FILE, 'rb')),  # Parquet file
        ('metadata_file', open(METADATA_FILE, 'rb')),  # JSON metadata file
    ]

    logger.info(f"Request: {url}")

    resp = requests.post(
        url=url,
        files=files,
        # timeout=10,
    )
    print(resp.status_code)

    assert resp.status_code == HTTPStatus.OK


@timing
@pytest.mark.parametrize("table_name, version", [
    ("2_test_v0_0_1", None),
    ("1_test_v0_0_1", ""),
    ("1_test_v0_0_1", "2"),
])
def test_get_table_data(api_connection, base_url, table_name, version):
    url = f'{base_url}/table/data'

    # Define the request payload with the table name and optional version
    payload = {
        "table_name": table_name,
        # "version": None  # You can set this to None to get the latest version
    }

    # special handling to test with and without the version attr in the payload
    if version == '':
        payload["version"] = None
    elif version is not None:
        payload["version"] = version

    logger.info(f"Request: {url}")

    resp = requests.get(
        url=url,
        params=payload
    )

    if resp.status_code != HTTPStatus.OK:
        print(resp.status_code, resp.text)

    assert resp.status_code == HTTPStatus.OK

    # Open a local file to save the downloaded Parquet file
    file_path = TMP_DIR / "get-data.parquet"
    with open(file_path, "wb") as file:
        file.write(resp.content)

    assert Path(file_path).stat().st_size > 1024


@timing
@pytest.mark.parametrize("task_id", [
    ("2",),
])
def test_get_table_info(api_connection, base_url, task_id):
    url = f'{base_url}/table/info'

    # Define the request payload with the table name and optional version
    payload = {
        "task_id": task_id,
    }

    logger.info(f"Request: {url}")

    resp = requests.get(
        url=url,
        params=payload
    )

    if resp.status_code != HTTPStatus.OK:
        print(resp.status_code, resp.text)

    if resp.status_code != HTTPStatus.OK:
        pytest.fail(f"Status code: {resp.status_code}, Response: {resp.text}")

    data = resp.json()

    logger.info(f"Table information: {data}")


@timing
@pytest.mark.parametrize("table_name", [
    ("1_test_v0_0_1",),
])
def test_get_table_versions(api_connection, base_url, table_name):
    url = f'{base_url}/table/versions/'

    # Define the request payload with the table name and optional version
    payload = {
        "table_name": "1_test_v0_0_1",
    }

    logger.info(f"Request: {url}")

    resp = requests.get(
        url=url,
        params=payload
    )

    if resp.status_code != HTTPStatus.OK:
        print(resp.status_code, resp.text)

    assert resp.status_code == HTTPStatus.OK

    data = resp.json()

    logger.info(f"Table versions: {data}")

    assert isinstance(data, list)
    assert len(data) > 1


# @timing
# @pytest.mark.parametrize("table_name", [
#     ("1_test_v0_0_1",),
# ])
# def run_sql_query_and_get_parquet(api_connection, base_url, table_name):
#     url = f'{base_url}/run-sql/'
#
#     # SQL query you want to execute on the Delta table
#     SQL_QUERY = f"""
#         SELECT *
#         FROM {table_name}
#         VERSION AS OF 99
#     """
#
#     # Prepare the request payload
#     payload = {
#         "table_name": table_name,
#         "sql_query": SQL_QUERY,
#     }
#
#     # Send the POST request
#     logger.info(f"Sending SQL query to: {url}")
#     resp = requests.post(url, json=payload)
#
#     # Check if the request was successful
#     if resp.status_code == HTTPStatus.OK:
#         # Generate a valid timestamp string for the filename
#         current_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#         filename = TMP_DIR / f"query_result_{current_timestamp}.parquet"
#
#         # Write the binary content directly to a file
#         with open(filename, 'wb') as f:
#             f.write(resp.content)  # Ensure the file is saved as binary data
#         print(f"Parquet file saved successfully at: {filename}")
#
#     else:
#         pytest.fail(f"Failed to run SQL query. Status code: {resp.status_code}, Response: {resp.text}")