from sbws.lib.resultdump import ResultError
from sbws.lib.resultdump import ResultSuccess
from sbws.lib.resultdump import Result
from sbws.lib.resultdump import write_result_to_datadir
from sbws.util.config import get_config
from sbws.util.parser import create_parser
import sbws.core.init
from tempfile import TemporaryDirectory
import pytest
import os
import time
import argparse


class _PseudoArguments(argparse.Namespace):
    '''
    Just enough of the argparse.Namespace (what you get when you do
    args = parser.parse_args()) to make get_config() happy

    >>> args = _PseudoArguments(directory='/home/matt/.sbws')
    >>> args.directory
    '/home/matt/.sbws'

    '''
    def __init__(self, **kw):
        for key in kw:
            setattr(self, key, kw[key])


@pytest.fixture(scope='session')
def parser():
    return create_parser()


@pytest.fixture(scope='function')
def empty_dotsbws(parser):
    '''
    Creates a ~/.sbws with nothing in it but a config.ini
    '''
    d = TemporaryDirectory()
    args = parser.parse_args(
        '-d {} --log-level DEBUG init'.format(d.name).split())
    conf = get_config(args)
    sbws.core.init.main(args, conf)
    return d


@pytest.fixture(scope='function')
def empty_dotsbws_datadir(empty_dotsbws):
    '''
    Creates a ~/.sbws with nothing in it but a config.ini and an empty datadir
    '''
    args = _PseudoArguments(directory=empty_dotsbws.name)
    conf = get_config(args)
    dd = conf['paths']['datadir']
    os.makedirs(dd, exist_ok=False)
    return empty_dotsbws


@pytest.fixture(scope='function')
def dotsbws_error_result(empty_dotsbws_datadir):
    '''
    Creates an ~/.sbws with a single fresh ResultError in it
    '''
    fp1 = 'A' * 40
    fp2 = 'B' * 40
    circ = [fp1, fp2]
    nick = 'CowSayWhat'
    relay_ip = '169.254.100.1'
    server_ip = '169.254.100.2'
    scanner_nick = 'SBWSscanner'
    msg = 'UnitTest error message'
    t = time.time()
    relay = Result.Relay(fp1, nick, relay_ip)
    result = ResultError(relay, circ, server_ip, scanner_nick, t=t, msg=msg)
    args = _PseudoArguments(directory=empty_dotsbws_datadir.name)
    conf = get_config(args)
    dd = conf['paths']['datadir']
    write_result_to_datadir(result, dd)
    return empty_dotsbws_datadir


@pytest.fixture(scope='function')
def dotsbws_success_result(empty_dotsbws_datadir):
    '''
    Creates an ~/.sbws with a single fresh ResultSuccess in it
    '''
    fp1 = 'A' * 40
    fp2 = 'B' * 40
    circ = [fp1, fp2]
    nick = 'CowSayWhat'
    relay_ip = '169.254.100.1'
    server_ip = '169.254.100.2'
    scanner_nick = 'SBWSscanner'
    rtts = [4.242]
    downloads = [{'duration': 4, 'amount': 40}]
    t = time.time()
    relay = Result.Relay(fp1, nick, relay_ip)
    result = ResultSuccess(rtts, downloads, relay, circ, server_ip,
                           scanner_nick, t=t)
    args = _PseudoArguments(directory=empty_dotsbws_datadir.name)
    conf = get_config(args)
    dd = conf['paths']['datadir']
    write_result_to_datadir(result, dd)
    return empty_dotsbws_datadir


@pytest.fixture(scope='function')
def dotsbws_success_result_one_relay(empty_dotsbws_datadir):
    '''
    Creates an ~/.sbws with a a couple of fresh ResultSuccess for one relay
    '''
    args = _PseudoArguments(directory=empty_dotsbws_datadir.name)
    conf = get_config(args)
    dd = conf['paths']['datadir']
    fp1 = 'A' * 40
    fp2 = 'B' * 40
    circ = [fp1, fp2]
    nick = 'CowSayWhat'
    relay_ip = '169.254.100.1'
    server_ip = '169.254.100.2'
    scanner_nick = 'SBWSscanner'
    rtts = [5, 25]
    downloads = [{'duration': 4, 'amount': 40}]
    t = time.time()
    relay = Result.Relay(fp1, nick, relay_ip)
    result = ResultSuccess(rtts, downloads, relay, circ, server_ip,
                           scanner_nick, t=t)
    write_result_to_datadir(result, dd)

    rtts = [10, 20]
    downloads = [{'duration': 4, 'amount': 80}]
    t = time.time()
    result = ResultSuccess(rtts, downloads, relay, circ, server_ip,
                           scanner_nick, t=t)
    write_result_to_datadir(result, dd)
    return empty_dotsbws_datadir


@pytest.fixture(scope='function')
def dotsbws_success_result_two_relays(empty_dotsbws_datadir):
    '''
    Creates an ~/.sbws with a a couple of fresh ResultSuccess for a couple or
    relays
    '''
    args = _PseudoArguments(directory=empty_dotsbws_datadir.name)
    conf = get_config(args)
    dd = conf['paths']['datadir']
    fp1 = 'A' * 40
    fp2 = 'C' * 40
    circ = [fp1, fp2]
    nick = 'CowSayWhat1'
    relay_ip = '169.254.100.1'
    server_ip = '169.254.100.3'
    scanner_nick = 'SBWSscanner'
    rtts = [5, 25]
    downloads = [{'duration': 4, 'amount': 40}]
    t = time.time()
    relay = Result.Relay(fp1, nick, relay_ip)
    result = ResultSuccess(rtts, downloads, relay, circ, server_ip,
                           scanner_nick, t=t)
    write_result_to_datadir(result, dd)

    rtts = [10, 20]
    downloads = [{'duration': 4, 'amount': 80}]
    t = time.time()
    result = ResultSuccess(rtts, downloads, relay, circ, server_ip,
                           scanner_nick, t=t)
    write_result_to_datadir(result, dd)

    fp1 = 'B' * 40
    circ = [fp1, fp2]
    nick = 'CowSayWhat2'
    relay_ip = '169.254.100.2'
    rtts = [50, 250]
    downloads = [{'duration': 4, 'amount': 400}]
    t = time.time()
    relay = Result.Relay(fp1, nick, relay_ip)
    result = ResultSuccess(rtts, downloads, relay, circ, server_ip,
                           scanner_nick, t=t)
    write_result_to_datadir(result, dd)

    rtts = [100, 200]
    downloads = [{'duration': 4, 'amount': 800}]
    t = time.time()
    result = ResultSuccess(rtts, downloads, relay, circ, server_ip,
                           scanner_nick, t=t)
    write_result_to_datadir(result, dd)

    return empty_dotsbws_datadir
