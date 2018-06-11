from unittest.mock import patch
from sbws.globals import RESULT_VERSION
from sbws.lib.resultdump import Result
from sbws.lib.resultdump import ResultSuccess
from sbws.lib.resultdump import ResultError
from sbws.lib.resultdump import ResultErrorAuth
from sbws.lib.resultdump import ResultErrorCircuit
from sbws.lib.resultdump import ResultErrorStream
from sbws.lib.resultdump import _ResultType
from tests.unit.globals import monotonic_time


@patch('time.time')
def test_Result(time_mock):
    '''
    A standard Result should not be convertible to a string because Result.type
    is not implemented.
    '''
    time_mock.side_effect = monotonic_time()
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    ed25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
    circ = [fp1, fp2]
    dest_url = 'http://example.com/sbws.bin'
    scanner_nick = 'sbwsscanner'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip, ed25519)
    r = Result(relay, circ, dest_url, scanner_nick)
    try:
        str(r)
    except NotImplementedError:
        pass
    else:
        assert None, 'Should have failed'


def test_Result_from_dict_bad_version():
    '''
    The first thing that is checked is the version field, and a wrong one
    should return None
    '''
    d = {'version': RESULT_VERSION + 1}
    r = Result.from_dict(d)
    assert r is None


def test_Result_from_dict_bad_type():
    '''
    If the result type string doesn't match any of the known types, then it
    should throw NotImplementedError
    '''
    d = {'version': RESULT_VERSION, 'type': 'NotARealType'}
    try:
        Result.from_dict(d)
    except NotImplementedError as e:
        assert str(e) == 'Unknown result type NotARealType'
    else:
        assert None, 'Should have failed'


@patch('time.time')
def test_ResultSuccess(time_mock):
    t = 2000
    time_mock.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    ed25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
    circ = [fp1, fp2]
    dest_url = 'http://example.com/sbws.bin'
    scanner_nick = 'sbwsscanner'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip, ed25519)
    rtts = [5, 25]
    downloads = [{'duration': 4, 'amount': 40}]
    r1 = ResultSuccess(rtts, downloads, relay, circ, dest_url, scanner_nick)
    r2 = ResultSuccess(rtts, downloads, relay, circ, dest_url, scanner_nick,
                       t=t)
    assert r1.downloads == downloads
    assert r1.rtts == rtts
    assert r1.nickname == nick
    assert r1.time == t
    assert r1.fingerprint == fp1
    assert r1.scanner == scanner_nick
    assert r1.type == _ResultType.Success
    assert r1.address == relay_ip
    assert r1.circ == circ
    assert r1.dest_url == dest_url
    assert r1.version == RESULT_VERSION
    assert str(r1) == str(r2)


@patch('time.time')
def test_ResultSuccess_from_dict(time_mock):
    t = 2000
    time_mock.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    ed25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
    circ = [fp1, fp2]
    dest_url = 'http://example.com/sbws.bin'
    scanner_nick = 'sbwsscanner'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip, ed25519)
    rtts = [5, 25]
    downloads = [{'duration': 4, 'amount': 40}]
    r1 = ResultSuccess(rtts, downloads, relay, circ, dest_url, scanner_nick)
    d = {
        'rtts': rtts, 'downloads': downloads, 'fingerprint': fp1,
        'nickname': nick, 'address': relay_ip, 'circ': circ,
        'dest_url': dest_url, 'scanner': scanner_nick,
        'version': RESULT_VERSION, 'type': _ResultType.Success, 'time': t,
        'master_key_ed25519': ed25519,
    }
    r2 = Result.from_dict(d)
    assert isinstance(r1, ResultSuccess)
    assert isinstance(r2, ResultSuccess)
    assert str(r1) == str(r2)


@patch('time.time')
def test_ResultError(time_mock):
    t = 2000
    time_mock.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    ed25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
    circ = [fp1, fp2]
    dest_url = 'http://example.com/sbws.bin'
    scanner_nick = 'sbwsscanner'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip, ed25519)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultError(relay, circ, dest_url, scanner_nick, msg=msg)
    r2 = ResultError(relay, circ, dest_url, scanner_nick, msg=msg, t=t)
    assert r1.msg == msg
    assert r1.nickname == nick
    assert r1.time == t
    assert r1.fingerprint == fp1
    assert r1.scanner == scanner_nick
    assert r1.type == _ResultType.Error
    assert r1.address == relay_ip
    assert r1.circ == circ
    assert r1.dest_url == dest_url
    assert r1.version == RESULT_VERSION
    assert str(r1) == str(r2)


@patch('time.time')
def test_ResultError_from_dict(time_mock):
    t = 2000
    time_mock.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    ed25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
    circ = [fp1, fp2]
    dest_url = 'http://example.com/sbws.bin'
    scanner_nick = 'sbwsscanner'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip, ed25519)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultError(relay, circ, dest_url, scanner_nick, msg=msg)
    d = {
        'msg': msg, 'fingerprint': fp1,
        'nickname': nick, 'address': relay_ip, 'circ': circ,
        'dest_url': dest_url, 'scanner': scanner_nick,
        'version': RESULT_VERSION, 'type': _ResultType.Error, 'time': t,
        'master_key_ed25519': ed25519,
    }
    r2 = Result.from_dict(d)
    assert isinstance(r1, ResultError)
    assert isinstance(r2, ResultError)
    assert str(r1) == str(r2)


@patch('time.time')
def test_ResultErrorCircuit(time_mock):
    t = 2000
    time_mock.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    ed25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
    circ = [fp1, fp2]
    dest_url = 'http://example.com/sbws.bin'
    scanner_nick = 'sbwsscanner'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip, ed25519)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorCircuit(relay, circ, dest_url, scanner_nick, msg=msg)
    r2 = ResultErrorCircuit(relay, circ, dest_url, scanner_nick, msg=msg,
                            t=t)
    assert r1.msg == msg
    assert r1.nickname == nick
    assert r1.time == t
    assert r1.fingerprint == fp1
    assert r1.scanner == scanner_nick
    assert r1.type == _ResultType.ErrorCircuit
    assert r1.address == relay_ip
    assert r1.circ == circ
    assert r1.dest_url == dest_url
    assert r1.version == RESULT_VERSION
    assert str(r1) == str(r2)


@patch('time.time')
def test_ResultErrorCircuit_from_dict(time_mock):
    t = 2000
    time_mock.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    ed25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
    circ = [fp1, fp2]
    dest_url = 'http://example.com/sbws.bin'
    scanner_nick = 'sbwsscanner'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip, ed25519)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorCircuit(relay, circ, dest_url, scanner_nick, msg=msg)
    d = {
        'msg': msg, 'fingerprint': fp1,
        'nickname': nick, 'address': relay_ip, 'circ': circ,
        'dest_url': dest_url, 'scanner': scanner_nick,
        'version': RESULT_VERSION, 'type': _ResultType.ErrorCircuit, 'time': t,
        'master_key_ed25519': ed25519,
    }
    r2 = Result.from_dict(d)
    assert isinstance(r1, ResultErrorCircuit)
    assert isinstance(r2, ResultErrorCircuit)
    assert str(r1) == str(r2)


@patch('time.time')
def test_ResultErrorStream(time_mock):
    t = 2000
    time_mock.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    ed25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
    circ = [fp1, fp2]
    dest_url = 'http://example.com/sbws.bin'
    scanner_nick = 'sbwsscanner'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip, ed25519)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorStream(relay, circ, dest_url, scanner_nick, msg=msg)
    r2 = ResultErrorStream(relay, circ, dest_url, scanner_nick, msg=msg,
                           t=t)
    assert r1.msg == msg
    assert r1.nickname == nick
    assert r1.time == t
    assert r1.fingerprint == fp1
    assert r1.scanner == scanner_nick
    assert r1.type == _ResultType.ErrorStream
    assert r1.address == relay_ip
    assert r1.circ == circ
    assert r1.dest_url == dest_url
    assert r1.version == RESULT_VERSION
    assert str(r1) == str(r2)


@patch('time.time')
def test_ResultErrorStream_from_dict(time_mock):
    t = 2000
    time_mock.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    ed25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
    circ = [fp1, fp2]
    dest_url = 'http://example.com/sbws.bin'
    scanner_nick = 'sbwsscanner'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip, ed25519)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorStream(relay, circ, dest_url, scanner_nick, msg=msg)
    d = {
        'msg': msg, 'fingerprint': fp1,
        'nickname': nick, 'address': relay_ip, 'circ': circ,
        'dest_url': dest_url, 'scanner': scanner_nick,
        'version': RESULT_VERSION, 'type': _ResultType.ErrorStream, 'time': t,
        'master_key_ed25519': ed25519,
    }
    r2 = Result.from_dict(d)
    assert isinstance(r1, ResultErrorStream)
    assert isinstance(r2, ResultErrorStream)
    assert str(r1) == str(r2)


@patch('time.time')
def test_ResultErrorAuth(time_mock):
    t = 2000
    time_mock.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    ed25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
    circ = [fp1, fp2]
    dest_url = 'http://example.com/sbws.bin'
    scanner_nick = 'sbwsscanner'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip, ed25519)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorAuth(relay, circ, dest_url, scanner_nick, msg=msg)
    r2 = ResultErrorAuth(relay, circ, dest_url, scanner_nick, msg=msg,
                         t=t)
    assert r1.msg == msg
    assert r1.nickname == nick
    assert r1.time == t
    assert r1.fingerprint == fp1
    assert r1.scanner == scanner_nick
    assert r1.type == _ResultType.ErrorAuth
    assert r1.address == relay_ip
    assert r1.circ == circ
    assert r1.dest_url == dest_url
    assert r1.version == RESULT_VERSION
    assert str(r1) == str(r2)


@patch('time.time')
def test_ResultErrorAuth_from_dict(time_mock):
    t = 2000
    time_mock.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    ed25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
    circ = [fp1, fp2]
    dest_url = 'http://example.com/sbws.bin'
    scanner_nick = 'sbwsscanner'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip, ed25519)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorAuth(relay, circ, dest_url, scanner_nick, msg=msg)
    d = {
        'msg': msg, 'fingerprint': fp1,
        'nickname': nick, 'address': relay_ip, 'circ': circ,
        'dest_url': dest_url, 'scanner': scanner_nick,
        'version': RESULT_VERSION, 'type': _ResultType.ErrorAuth, 'time': t,
        'master_key_ed25519': ed25519,
    }
    r2 = Result.from_dict(d)
    assert isinstance(r1, ResultErrorAuth)
    assert isinstance(r2, ResultErrorAuth)
    assert str(r1) == str(r2)
