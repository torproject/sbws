from sbws.lib.resultdump import ResultError
from sbws.lib.resultdump import ResultSuccess
from sbws.lib.resultdump import Result
from sbws.util.config import get_config
from sbws.util.parser import create_parser
import sbws.commands.init
from tempfile import TemporaryDirectory
import pytest
import os
import time
from datetime import date


class MockPastlyLogger:
    def __init__(self, *a, _do_print=False, **kw):
        self._logged_lines = []
        self._do_print = _do_print
        pass

    def debug(self, *s):
        self._logged_lines.append(' '.join(str(_) for _ in s))
        if self._do_print:
            print(*s)

    def info(self, *s):
        return self.debug(*s)

    def notice(self, *s):
        return self.info(*s)

    def warn(self, *s):
        return self.notice(*s)

    def error(self, *s):
        return self.warn(*s)

    def test_get_logged_lines(self, clear=True):
        '''
        Return a generator containing all the lines we have logged. Optionally
        clear the cache of lines after returning them all
        '''
        for line in self._logged_lines:
            yield line
        if clear:
            self._logged_lines = []

    def test_set_new_test(self):
        '''
        Clear any cached data that we might have accumulated from previous
        tests
        '''
        self._logged_lines = []


@pytest.fixture(scope='module')
def log():
    pl = MockPastlyLogger()
    return pl


@pytest.fixture(scope='session')
def parser():
    return create_parser()


@pytest.fixture(scope='function')
def empty_dotsbws(log, parser):
    '''
    Creates a ~/.sbws with nothing in it but a config.ini
    '''
    d = TemporaryDirectory()
    args = parser.parse_args('-d {} -vvvv init'.format(d.name).split())
    conf = get_config(args, log_fn=log.debug)
    sbws.commands.init.main(args, conf, log)
    return d


@pytest.fixture(scope='function')
def empty_dotsbws_datadir(empty_dotsbws):
    '''
    Creates a ~/.sbws with nothing in it but a config.ini and an empty datadir
    '''
    dname = os.path.join(empty_dotsbws.name, 'datadir')
    os.makedirs(dname, exist_ok=False)
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
    client_nick = 'SBWSclient'
    msg = 'UnitTest error message'
    t = time.time()
    relay = Result.Relay(fp1, nick, relay_ip)
    result = ResultError(relay, circ, server_ip, client_nick, t=t, msg=msg)

    dt = date.fromtimestamp(t)
    ext = '.txt'
    fname = os.path.join(empty_dotsbws_datadir.name, 'datadir',
                         '{}{}'.format(dt, ext))
    with open(fname, 'at') as fd:
        fd.write('{}\n'.format(str(result)))
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
    client_nick = 'SBWSclient'
    rtts = [4.242]
    downloads = [{'duration': 4, 'amount': 40}]
    t = time.time()
    relay = Result.Relay(fp1, nick, relay_ip)
    result = ResultSuccess(rtts, downloads, relay, circ, server_ip,
                           client_nick, t=t)
    dt = date.fromtimestamp(t)
    ext = '.txt'
    fname = os.path.join(empty_dotsbws_datadir.name, 'datadir',
                         '{}{}'.format(dt, ext))
    with open(fname, 'at') as fd:
        fd.write('{}\n'.format(str(result)))
    return empty_dotsbws_datadir
