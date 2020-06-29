"""Common pytest configuration for unit and integration tests."""
import pytest
import os.path
from unittest import mock

from freezegun import freeze_time
from stem import descriptor

from sbws import settings
from sbws.lib import relaylist
from sbws.lib import relayprioritizer
from sbws.lib import resultdump
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


@pytest.fixture(scope="session")
def server_descriptors(root_data_path):
    p = os.path.join(root_data_path, "2020-02-29-10-05-00-server-descriptors")
    server_descriptors = descriptor.parse_file(p)
    server_descriptors_list = list(server_descriptors)
    return server_descriptors_list


@pytest.fixture(scope="session")
def server_descriptor(server_descriptors):
    return server_descriptors[0]


@pytest.fixture(scope="session")
def router_status(server_descriptor, router_statuses):
    rs = [
        ns
        for ns in router_statuses
        if ns.fingerprint == server_descriptor.fingerprint
    ][0]
    return rs


# Because of the function scoped `args` in `tests.unit.conftest`, this has to
# be function scoped too.
@pytest.fixture(scope='function')
def relay_list(args, conf, controller):
    """Returns a RelayList containing the Relays in the controller"""
    with freeze_time("2020-02-29 10:00:00"):
        return relaylist.RelayList(args, conf, controller)


@pytest.fixture(scope='function')
def result_dump(args, conf):
    """Returns a ResultDump without Results"""
    # To stop the thread that would be waiting for new results
    settings.set_end_event()
    return resultdump.ResultDump(args, conf)


@pytest.fixture(scope="function")
def relay_prioritizer(args, conf_results, relay_list, result_dump):
    """
    Returns a RelayPrioritizer with a RelayList and a ResultDump.
    """
    return relayprioritizer.RelayPrioritizer(
        args, conf_results, relay_list, result_dump
    )
