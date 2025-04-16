# python standard library


# 3rd party libraries
import pytest

# package imports
from app.api_endpoints import api_server


LOCAL_PORT = 5001
DOCKER_PORT = 5000

LOCAL_BASE_URL = f'http://127.0.0.1'
REMOTE_SERVER_BASE_URL = f'http://inli071-v.in.de.conti.de'


test_settings = {
    'local_dev': f"{LOCAL_BASE_URL}:{LOCAL_PORT}",
    'local_docker': f"{LOCAL_BASE_URL}:{DOCKER_PORT}",
    'staging_server': f"{REMOTE_SERVER_BASE_URL}:{DOCKER_PORT}",
}

@pytest.fixture(scope='session')
def test_mode():
    # return 'local_dev'
    return 'local_docker'


@pytest.fixture(scope='session')
def api_connection(test_mode):
    if test_mode == 'local_dev':
        with api_server(LOCAL_PORT):
            yield
    elif test_mode == 'local_docker':
        yield
    elif test_mode == 'staging_server':
        yield
    else:
        raise ValueError(f"No setup defined for '{test_mode}'")


@pytest.fixture(scope='session')
def base_url(test_mode):
    return test_settings[test_mode]