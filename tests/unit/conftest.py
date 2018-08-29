"""pytest configuration for unit tests."""
import argparse
import pytest
from datetime import datetime
import os

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
RTTS1 = [
    0.2943556308746338, 0.2885427474975586, 0.2802879810333252,
    0.28124427795410156, 0.2827129364013672, 0.2901294231414795,
    0.2784590721130371, 0.2838578224182129, 0.2842121124267578,
    0.28656768798828125
]
RTTS2 = [
    0.9097037315368652, 0.9293286800384521, 2.3764255046844482,
    0.869133710861206, 0.8188621997833252, 0.9046516418457031,
    1.3477752208709717, 0.8118226528167725, 0.8821918964385986,
    0.8746812343597412
]
RTTS3 = [
    0.510988712310791, 0.4889242649078369, 0.5003941059112549,
    0.49333715438842773, 0.5000274181365967, 0.5426476001739502,
    0.5190870761871338, 0.4908745288848877, 0.5516133308410645,
    0.4995298385620117
]
DOWNLOADS1 = [
    {"duration": 28.01000952720642, "amount": 25916542},
    {"duration": 28.203476428985596, "amount": 25916542},
    {"duration": 27.897520780563354, "amount": 25916542},
    {"duration": 29.330559492111206, "amount": 25916542},
    {"duration": 27.93175745010376, "amount": 25916542}
]
DOWNLOADS2 = [
    {"duration": 23.68175435066223, "amount": 81920},
    {"duration": 27.667736768722534, "amount": 81920},
    {"duration": 31.022956371307373, "amount": 81920},
    {"duration": 33.020694971084595, "amount": 81920},
    {"duration": 33.59471535682678, "amount": 81920}
]
DOWNLOADS3 = [
    {"duration": 30.008347988128662, "amount": 644411},
    {"duration": 30.73241639137268, "amount": 644411},
    {"duration": 31.845987796783447, "amount": 644411},
    {"duration": 29.703084230422974, "amount": 644411},
    {"duration": 30.438726663589478, "amount": 644411}
]
SCANNER = "test"
AVG_BW = 966080
OBS_BW = 524288

RELAY1 = Result.Relay(FP1, NICK1, IP1, ED25519,
                      average_bandwidth=AVG_BW, observed_bandwidth=OBS_BW)
RELAY2 = Result.Relay(FP2, NICK2, IP2, ED25519)

RESULT = Result(RELAY1, CIRC12, DEST_URL, SCANNER, t=TIME1)
RESULT_SUCCESS1 = ResultSuccess(RTTS1, DOWNLOADS1, RELAY1, CIRC12, DEST_URL,
                                SCANNER, t=TIME1)
RESULT_SUCCESS2 = ResultSuccess(RTTS2, DOWNLOADS2, RELAY2, CIRC21, DEST_URL,
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
    "relay_average_bandwidth": AVG_BW,
    "relay_observed_bandwidth": OBS_BW
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
    "rtts": RTTS1,
    "type": "success",
    "downloads": DOWNLOADS1,
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
def test_config_path(tmpdir):
    """"""
    config = tmpdir.join('.sbws.ini')
    return config


@pytest.fixture(scope='function')
def args(sbwshome_empty, parser, test_config_path):
    """Args with sbws home in the tests tmp dir."""
    args = _PseudoArguments(config=test_config_path, output=sbwshome_empty,
                            scale=False, log_level='debug')
    return args


@pytest.fixture(scope='function')
def conf(sbwshome_empty):
    """Default configuration with sbws home in the tmp test dir."""
    conf = _get_default_config()
    conf['paths']['sbws_home'] = sbwshome_empty
    return conf


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
def sbwshome_error_result(sbwshome_only_datadir, conf):
    '''
    Creates an ~/.sbws with a single fresh ResultError in it
    '''
    dd = conf.getpath('paths', 'datadir')
    write_result_to_datadir(RESULT_ERROR_STREAM, dd)
    return sbwshome_only_datadir


@pytest.fixture(scope='function')
def sbwshome_success_result(sbwshome_only_datadir, conf):
    '''
    Creates an ~/.sbws with a single fresh ResultSuccess in it
    '''
    dd = conf.getpath('paths', 'datadir')
    write_result_to_datadir(RESULT_SUCCESS1, dd)
    return sbwshome_only_datadir


@pytest.fixture(scope='function')
def sbwshome_success_result_one_relay(sbwshome_only_datadir, conf):
    '''
    Creates an ~/.sbws with a a couple of fresh ResultSuccess for one relay
    '''
    dd = conf.getpath('paths', 'datadir')
    write_result_to_datadir(RESULT_SUCCESS1, dd)
    write_result_to_datadir(RESULT_SUCCESS1, dd)
    return sbwshome_only_datadir


@pytest.fixture(scope='function')
def sbwshome_success_result_two_relays(sbwshome_only_datadir, conf):
    '''
    Creates an ~/.sbws with a a couple of fresh ResultSuccess for a couple or
    relays
    '''
    dd = conf.getpath('paths', 'datadir')
    write_result_to_datadir(RESULT_SUCCESS1, dd)
    write_result_to_datadir(RESULT_SUCCESS1, dd)
    write_result_to_datadir(RESULT_SUCCESS2, dd)
    write_result_to_datadir(RESULT_SUCCESS2, dd)
    return sbwshome_only_datadir
