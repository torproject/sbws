"""pytest configuration for unit tests."""
import argparse
import pytest
from datetime import datetime
import os

from sbws.core import init
from sbws.globals import RESULT_VERSION
from sbws.lib.resultdump import (ResultErrorStream, ResultSuccess, Result)
from sbws.lib.resultdump import write_result_to_datadir
from sbws.util.config import _get_default_config


TIME1 = 1529232277.9028733
TIME2 = datetime.utcnow().timestamp()
FP1 = 'A' * 40
FP2 = 'B' * 40
ED25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
CIRC12 = [FP1, FP2]
CIRC21 = [FP2, FP1]
DEST_URL = 'http://example.com/sbws.bin'
NICK1 = 'A'
NICK2 = 'B'
IP1 = '169.254.100.1'
IP2 = '169.254.100.2'
RTTS = [5, 25]
DOWNLOADS = [{'duration': 4, 'amount': 40}]
SCANNER = "test"
AVG_BW = 1024 * 1024

RELAY1 = Result.Relay(FP1, NICK1, IP1, ED25519,
                      average_bandwidth=AVG_BW)
RELAY2 = Result.Relay(FP1, NICK2, IP2, ED25519)

RESULT = Result(RELAY1, CIRC12, DEST_URL, SCANNER, t=TIME1)
RESULT_SUCCESS1 = ResultSuccess(RTTS, DOWNLOADS, RELAY1, CIRC12, DEST_URL,
                                SCANNER, t=TIME1)
RESULT_SUCCESS2 = ResultSuccess(RTTS, DOWNLOADS, RELAY2, CIRC21, DEST_URL,
                                SCANNER, t=TIME2)
RESULT_ERROR_STREAM = ResultErrorStream(RELAY1, CIRC12, DEST_URL, SCANNER,
                                        t=TIME1, msg="Something bad")

RESULTDICT_IP_CHANGED = {FP1: [RESULT_SUCCESS1, RESULT_SUCCESS2]}
RESULTDICT_IP_NOT_CHANGED = {FP1: [RESULT_SUCCESS1, RESULT_SUCCESS1]}

RELAY_DICT = {
    "fingerprint": FP1,
    "address": IP1,
    "nickname": NICK1,
    "master_key_ed25519": ED25519,
    "relay_average_bandwidth": AVG_BW
}

BASE_RESULT_NO_RELAY_DICT = {
    "dest_url": DEST_URL,
    "time": TIME1,
    "circ": CIRC12,
    "version": RESULT_VERSION,
    "scanner": SCANNER,
}

BASE_RESULT_DICT = RELAY_DICT.copy()
BASE_RESULT_DICT.update(BASE_RESULT_NO_RELAY_DICT)

RESULT_ERROR_STREAM_DICT = BASE_RESULT_DICT.copy()
RESULT_ERROR_STREAM_DICT.update({
    "type": "error-stream",
    "msg": "Something bad",
})

RESULT_SUCCESS_DICT = BASE_RESULT_DICT.copy()
RESULT_SUCCESS_DICT.update({
    "rtts": RTTS,
    "type": "success",
    "downloads": DOWNLOADS,
})


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


@pytest.fixture(scope='function')
def tmpdir(tmpdir_factory, request):
    """Create a tmp dir for the tests"""
    base = str(hash(request.node.nodeid))[:3]
    bn = tmpdir_factory.mktemp(base)
    return bn


@pytest.fixture(scope='function')
def sbwshome_empty(tmpdir):
    """Create sbws home inside of the tests tmp dir without initializing."""
    home = tmpdir.join('.sbws')
    os.makedirs(home.strpath, exist_ok=True)
    return home.strpath


@pytest.fixture(scope='function')
def sbwshome_only_datadir(sbwshome_empty):
    """Create sbws home inside of the tests tmp dir with only datadir."""
    os.makedirs(os.path.join(sbwshome_empty, 'datadir'), exist_ok=True)
    return sbwshome_empty


@pytest.fixture(scope='function')
def args(sbwshome_empty, parser):
    """Args with sbws home in the tests tmp dir."""
    args = _PseudoArguments(directory=sbwshome_empty, output=sbwshome_empty,
                            scale=False, log_level='debug', v3bw=False)
    return args


@pytest.fixture(scope='function')
def conf(sbwshome_empty):
    """Default configuration with sbws home in the tmp test dir."""
    conf = _get_default_config()
    conf['paths']['sbws_home'] = sbwshome_empty
    return conf


@pytest.fixture(scope='function')
def sbwshome_config(sbwshome_empty, args, conf):
    """Create sbws home inside of the tests tmp dir with only datadir."""
    init.main(args, conf)
    return sbwshome_empty


@pytest.fixture(scope='function')
def sbwshome(sbwshome_only_datadir, args, conf):
    """Create sbws home inside of the tests tmp dir."""
    os.makedirs(os.path.join(sbwshome_only_datadir, 'v3bw'), exist_ok=True)
    init.main(args, conf)
    return conf['paths']['sbws_home']


@pytest.fixture()
def result():
    return RESULT


@pytest.fixture()
def result_success():
    return RESULT_SUCCESS1


@pytest.fixture()
def result_success_dict():
    return RESULT_SUCCESS_DICT


@pytest.fixture()
def result_error_stream_dict():
    return RESULT_ERROR_STREAM_DICT


@pytest.fixture()
def result_error_stream():
    return RESULT_ERROR_STREAM


@pytest.fixture()
def resultdict_ip_changed():
    return RESULTDICT_IP_CHANGED


@pytest.fixture()
def resultdict_ip_not_changed():
    return RESULTDICT_IP_NOT_CHANGED


@pytest.fixture()
def resultdict_ip_changed_trimmed():
    return {FP1: [RESULT_SUCCESS2]}


@pytest.fixture(scope='function')
def sbwshome_error_result(sbwshome, conf):
    '''
    Creates an ~/.sbws with a single fresh ResultError in it
    '''
    dd = conf['paths']['datadir']
    write_result_to_datadir(RESULT_ERROR_STREAM, dd)
    return sbwshome


@pytest.fixture(scope='function')
def sbwshome_success_result(sbwshome, conf):
    '''
    Creates an ~/.sbws with a single fresh ResultSuccess in it
    '''
    dd = conf['paths']['datadir']
    write_result_to_datadir(RESULT_SUCCESS1, dd)
    return sbwshome


@pytest.fixture(scope='function')
def sbwshome_success_result_one_relay(sbwshome, conf):
    '''
    Creates an ~/.sbws with a a couple of fresh ResultSuccess for one relay
    '''
    dd = conf['paths']['datadir']
    write_result_to_datadir(RESULT_SUCCESS1, dd)
    write_result_to_datadir(RESULT_SUCCESS1, dd)
    return sbwshome


@pytest.fixture(scope='function')
def sbwshome_success_result_two_relays(sbwshome, conf):
    '''
    Creates an ~/.sbws with a a couple of fresh ResultSuccess for a couple or
    relays
    '''
    dd = conf['paths']['datadir']
    write_result_to_datadir(RESULT_SUCCESS1, dd)
    write_result_to_datadir(RESULT_SUCCESS1, dd)
    write_result_to_datadir(RESULT_SUCCESS2, dd)
    write_result_to_datadir(RESULT_SUCCESS2, dd)
    return sbwshome
