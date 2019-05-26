"""Common pytest configuration for unit and integration tests."""
import argparse
import os.path
import pytest
from unittest import mock

from sbws.lib import resultdump
from sbws.util import config
from sbws.util.parser import create_parser


FAKE_TIME = 1557556118


@pytest.fixture(scope='session')
def parser():
    return create_parser()


@pytest.fixture()
def datadir(request):
    """get, read, open test files from the tests "data" directory."""
    class D:
        def __init__(self, basepath):
            self.basepath = basepath

        def open(self, name, mode="r"):
            return self.basepath.join(name).open(mode)

        def join(self, name):
            return self.basepath.join(name).strpath

        def read(self, name):
            with self.open(name, "r") as f:
                return f.read()

        def readlines(self, name):
            with self.open(name, "r") as f:
                return f.readlines()
    return D(request.fspath.dirpath("data"))


@pytest.fixture()
def tests_data_dir(scope="global"):
    """Root data directory, common to all the tests."""
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(here, "data")


@pytest.fixture()
def sbws_dir(tests_data_dir):
    return os.path.join(tests_data_dir, ".sbws")


# The following fixtures are similar to the ones defined in unit and
# integration sub-directories, but they are for the tests data to be read,
# not to write.
@pytest.fixture()
def sbws_args(tests_data_dir):
    config_fpath = os.path.join(tests_data_dir, ".sbws.ini")
    sbws_args = argparse.Namespace(**{'config': config_fpath})
    return sbws_args


@pytest.fixture()
def sbws_conf(sbws_args, sbws_dir):
    """Default configuration with sbws home in the tmp test dir."""
    conf = config.get_config(sbws_args)
    conf['paths']['sbws_home'] = sbws_dir
    conf['paths']['v3bw_fname'] = "${v3bw_dname}/latest.v3bw"
    return conf


@pytest.fixture()
@mock.patch('time.time')
def measurements(mock_time, sbws_conf):
    # Because load_recent_results_in_datadir will use time.time()
    # to decide which results are recent.
    mock_time.return_value = FAKE_TIME
    measurements = resultdump \
        .load_recent_results_in_datadir(
            sbws_conf.getint('general', 'data_period'),
            sbws_conf.getpath('paths', 'datadir'))
    return measurements


@pytest.fixture
def bandwidth_file_headers():
    d = {
        'earliest_bandwidth': "2019-05-11T06:26:41",
        'file_created': "2019-05-11T06:32:32",
        'generator_started': "2019-05-11T06:26:28",
        'latest_bandwidth': "2019-05-11T06:28:38",
    }
    return d
