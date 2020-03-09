"""Common pytest configuration for unit and integration tests."""
import pytest
import os.path
from unittest import mock

from stem import descriptor

from sbws.util.parser import create_parser


@pytest.fixture(scope='session')
def parser():
    return create_parser()


@pytest.fixture()
def datadir(request):
    """get, read, open test files from the tests relative "data" directory."""
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


@pytest.fixture(scope="session")
def root_data_path():
    """Path to the data dir in the tests root, for both unit and integration
    tests.
    """
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data",)


@pytest.fixture(scope="session")
def router_statuses(root_data_path):
    p = os.path.join(root_data_path, "2020-02-29-10-00-00-consensus")
    network_statuses = descriptor.parse_file(p)
    network_statuses_list = list(network_statuses)
    return network_statuses_list


@pytest.fixture(scope="session")
def router_statuses_1h_later(root_data_path):
    p = os.path.join(root_data_path, "2020-02-29-11-00-00-consensus")
    network_statuses = descriptor.parse_file(p)
    network_statuses_list = list(network_statuses)
    return network_statuses_list


@pytest.fixture(scope="session")
def router_statuses_5days_later(root_data_path):
    p = os.path.join(root_data_path, "2020-03-05-10-00-00-consensus")
    network_statuses = descriptor.parse_file(p)
    network_statuses_list = list(network_statuses)
    return network_statuses_list


@pytest.fixture(scope="session")
def controller(router_statuses):
    controller = mock.Mock()
    controller.get_network_statuses.return_value = router_statuses
    return controller


@pytest.fixture(scope="session")
def controller_1h_later(router_statuses_1h_later):
    controller = mock.Mock()
    controller.get_network_statuses.return_value = router_statuses_1h_later
    return controller


@pytest.fixture(scope="session")
def controller_5days_later(router_statuses_5days_later):
    controller = mock.Mock()
    controller.get_network_statuses.return_value = router_statuses_5days_later
    return controller
