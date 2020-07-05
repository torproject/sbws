"""pytest configuration for integration tests."""
import argparse
import pytest
import os

from sbws.lib.circuitbuilder import GapsCircuitBuilder as CB
from sbws.lib.destination import DestinationList
from sbws.lib.relaylist import RelayList
from sbws.util.config import _get_default_config
from sbws.util.stem import launch_tor


class _PseudoArguments(argparse.Namespace):

    """Just enough of the argparse.Namespace (what you get when you do
    args = parser.parse_args()) to make get_config() happy

    >>> args = _PseudoArguments(directory='/home/matt/.sbws')
    >>> args.directory
    '/home/matt/.sbws'

    """

    def __init__(self, **kw):
        for key in kw:
            setattr(self, key, kw[key])


@pytest.fixture(scope='session')
def tmpdir(tmpdir_factory, request):
    """Create a tmp dir for the tests"""
    base = str(hash(request.node.nodeid))[:3]
    bn = tmpdir_factory.mktemp(base)
    return bn


@pytest.fixture(scope='session')
def sbwshome_empty(tmpdir):
    """Create sbws home inside of the test net tmp dir without initializing."""
    home = "/tmp/.sbws"
    os.makedirs(home, exist_ok=True)
    return home


@pytest.fixture(scope='session')
def sbwshome_dir(sbwshome_empty):
    """Create sbws home inside of the test net tmp dir without initializing."""
    os.makedirs(os.path.join(sbwshome_empty, 'datadir'), exist_ok=True)
    return sbwshome_empty


@pytest.fixture(scope='session')
def test_config_path(tmpdir):
    """"""
    config = tmpdir.join('.sbws.ini')
    return config


@pytest.fixture(scope='session')
def args(sbwshome_empty, parser, test_config_path):
    """Args with sbws home in the tests tmp dir."""
    args = _PseudoArguments(config=test_config_path, output=sbwshome_empty,
                            scale=False, log_level='debug')
    return args


@pytest.fixture(scope='session')
def conf(sbwshome_dir):
    """Default configuration with sbws home in the tmp test dir."""
    conf = _get_default_config()
    conf['paths']['sbws_home'] = sbwshome_dir
    conf["paths"]["state_fpath"] = os.path.join(sbwshome_dir, "state.dat")
    conf['tor']['run_dpath'] = os.path.join(sbwshome_dir, 'tor', 'run')
    conf['destinations']['foo'] = 'on'
    conf['destinations.foo'] = {}
    # The test server is not using TLS. Ideally it should also support TLS
    # If the url would start with https but the request is not using TLS,
    # the request would hang.
    conf['destinations.foo']['url'] = 'http://127.0.0.1:28888/sbws.bin'
    conf['tor']['extra_lines'] = """  # noqa: E501
DirAuthority auth1 orport=2002 no-v2 v3ident=3668D8876241ADD04B53CAB08E7442BDE6EC9A06 127.10.0.1:2003 AA45C13025C037F056E734169891878ED0880231
DirAuthority auth2 orport=2002 no-v2 v3ident=100036EB705CDCFB1746B450C23B861F554A3630 127.10.0.2:2003 E7B3C9A0040D628DAC88B0251AE6334D28E8F531
DirAuthority auth3 orport=2002 no-v2 v3ident=4EC8AA0B0F120205EEE32C9918F1D99214ADF518 127.10.0.3:2003 35E3B8BB71C81355649AEC5862ECB7ED7EFDBC5C
TestingTorNetwork 1
NumCPUs 1
LogTimeGranularity 1
SafeLogging 0
"""
    return conf


@pytest.fixture(scope='session')
def persistent_launch_tor(conf):
    cont = launch_tor(conf)
    return cont


@pytest.fixture(scope='session')
def rl(args, conf, persistent_launch_tor):
    return RelayList(args, conf, persistent_launch_tor)


@pytest.fixture(scope='session')
def cb(args, conf, persistent_launch_tor, rl):
    return CB(args, conf, persistent_launch_tor, rl)


@pytest.fixture(scope='session')
def dests(args, conf, persistent_launch_tor, cb, rl):
    dests, error_msg = DestinationList.from_config(conf, cb, rl,
                                                   persistent_launch_tor)
    assert dests, error_msg
    return dests


# @pytest.fixture(scope='session')
