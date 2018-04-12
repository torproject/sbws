from unittest.mock import patch
from sbws import res_proto_ver
from sbws.lib.resultdump import Result
from sbws.lib.resultdump import ResultSuccess
from sbws.lib.resultdump import ResultError
from sbws.lib.resultdump import ResultErrorAuth
from sbws.lib.resultdump import ResultErrorCircuit
from sbws.lib.resultdump import ResultErrorStream
from sbws.lib.resultdump import _ResultType
from tests.globals import monotonic_time


@patch('sbws.lib.resultdump.time_now')
def test_Result(time_now):
    '''
    A standard Result should not be convertible to a string because Result.type
    is not implemented.
    '''
    time_now.side_effect = monotonic_time()
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    circ = [fp1, fp2]
    server_host = '::1'
    client_nick = 'sbwsclient'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip)
    r = Result(relay, circ, server_host, client_nick)
    try:
        str(r)
    except NotImplementedError:
        pass
    else:
        assert None, 'Should have failed'
    print(r.time)


def test_Result_from_dict_bad_version():
    '''
    The first thing that is checked is the version field, and a wrong one
    should return None
    '''
    d = {'version': res_proto_ver + 1}
    r = Result.from_dict(d)
    assert r is None


def test_Result_from_dict_bad_type():
    '''
    If the result type string doesn't match any of the known types, then it
    should throw NotImplementedError
    '''
    d = {'version': res_proto_ver, 'type': 'NotARealType'}
    try:
        Result.from_dict(d)
    except NotImplementedError as e:
        assert str(e) == 'Unknown result type NotARealType'
    else:
        assert None, 'Should have failed'


@patch('sbws.lib.resultdump.time_now')
def test_ResultSuccess(time_now):
    t = 2000
    time_now.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    circ = [fp1, fp2]
    server_host = '::1'
    client_nick = 'sbwsclient'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip)
    rtts = [5, 25]
    downloads = [{'duration': 4, 'amount': 40}]
    r1 = ResultSuccess(rtts, downloads, relay, circ, server_host, client_nick)
    r2 = ResultSuccess(rtts, downloads, relay, circ, server_host, client_nick,
                       t=t)
    assert r1.downloads == downloads
    assert r1.rtts == rtts
    assert r1.nickname == nick
    assert r1.time == t
    assert r1.fingerprint == fp1
    assert r1.scanner == client_nick
    assert r1.type == _ResultType.Success
    assert r1.address == relay_ip
    assert r1.circ == circ
    assert r1.server_host == server_host
    assert r1.version == res_proto_ver
    assert str(r1) == str(r2)


@patch('sbws.lib.resultdump.time_now')
def test_ResultSuccess_from_dict(time_now):
    t = 2000
    time_now.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    circ = [fp1, fp2]
    server_host = '::1'
    client_nick = 'sbwsclient'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip)
    rtts = [5, 25]
    downloads = [{'duration': 4, 'amount': 40}]
    r1 = ResultSuccess(rtts, downloads, relay, circ, server_host, client_nick)
    d = {
        'rtts': rtts, 'downloads': downloads, 'fingerprint': fp1,
        'nickname': nick, 'address': relay_ip, 'circ': circ,
        'server_host': server_host, 'scanner': client_nick,
        'version': res_proto_ver, 'type': _ResultType.Success, 'time': t,
    }
    r2 = Result.from_dict(d)
    assert isinstance(r1, ResultSuccess)
    assert isinstance(r2, ResultSuccess)
    assert str(r1) == str(r2)


@patch('sbws.lib.resultdump.time_now')
def test_ResultError(time_now):
    t = 2000
    time_now.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    circ = [fp1, fp2]
    server_host = '::1'
    client_nick = 'sbwsclient'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultError(relay, circ, server_host, client_nick, msg=msg)
    r2 = ResultError(relay, circ, server_host, client_nick, msg=msg, t=t)
    assert r1.msg == msg
    assert r1.nickname == nick
    assert r1.time == t
    assert r1.fingerprint == fp1
    assert r1.scanner == client_nick
    assert r1.type == _ResultType.Error
    assert r1.address == relay_ip
    assert r1.circ == circ
    assert r1.server_host == server_host
    assert r1.version == res_proto_ver
    assert str(r1) == str(r2)


@patch('sbws.lib.resultdump.time_now')
def test_ResultError_from_dict(time_now):
    t = 2000
    time_now.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    circ = [fp1, fp2]
    server_host = '::1'
    client_nick = 'sbwsclient'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultError(relay, circ, server_host, client_nick, msg=msg)
    d = {
        'msg': msg, 'fingerprint': fp1,
        'nickname': nick, 'address': relay_ip, 'circ': circ,
        'server_host': server_host, 'scanner': client_nick,
        'version': res_proto_ver, 'type': _ResultType.Error, 'time': t,
    }
    r2 = Result.from_dict(d)
    assert isinstance(r1, ResultError)
    assert isinstance(r2, ResultError)
    assert str(r1) == str(r2)


@patch('sbws.lib.resultdump.time_now')
def test_ResultErrorCircuit(time_now):
    t = 2000
    time_now.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    circ = [fp1, fp2]
    server_host = '::1'
    client_nick = 'sbwsclient'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorCircuit(relay, circ, server_host, client_nick, msg=msg)
    r2 = ResultErrorCircuit(relay, circ, server_host, client_nick, msg=msg,
                            t=t)
    assert r1.msg == msg
    assert r1.nickname == nick
    assert r1.time == t
    assert r1.fingerprint == fp1
    assert r1.scanner == client_nick
    assert r1.type == _ResultType.ErrorCircuit
    assert r1.address == relay_ip
    assert r1.circ == circ
    assert r1.server_host == server_host
    assert r1.version == res_proto_ver
    assert str(r1) == str(r2)


@patch('sbws.lib.resultdump.time_now')
def test_ResultErrorCircuit_from_dict(time_now):
    t = 2000
    time_now.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    circ = [fp1, fp2]
    server_host = '::1'
    client_nick = 'sbwsclient'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorCircuit(relay, circ, server_host, client_nick, msg=msg)
    d = {
        'msg': msg, 'fingerprint': fp1,
        'nickname': nick, 'address': relay_ip, 'circ': circ,
        'server_host': server_host, 'scanner': client_nick,
        'version': res_proto_ver, 'type': _ResultType.ErrorCircuit, 'time': t,
    }
    r2 = Result.from_dict(d)
    assert isinstance(r1, ResultErrorCircuit)
    assert isinstance(r2, ResultErrorCircuit)
    assert str(r1) == str(r2)


@patch('sbws.lib.resultdump.time_now')
def test_ResultErrorStream(time_now):
    t = 2000
    time_now.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    circ = [fp1, fp2]
    server_host = '::1'
    client_nick = 'sbwsclient'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorStream(relay, circ, server_host, client_nick, msg=msg)
    r2 = ResultErrorStream(relay, circ, server_host, client_nick, msg=msg,
                           t=t)
    assert r1.msg == msg
    assert r1.nickname == nick
    assert r1.time == t
    assert r1.fingerprint == fp1
    assert r1.scanner == client_nick
    assert r1.type == _ResultType.ErrorStream
    assert r1.address == relay_ip
    assert r1.circ == circ
    assert r1.server_host == server_host
    assert r1.version == res_proto_ver
    assert str(r1) == str(r2)


@patch('sbws.lib.resultdump.time_now')
def test_ResultErrorStream_from_dict(time_now):
    t = 2000
    time_now.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    circ = [fp1, fp2]
    server_host = '::1'
    client_nick = 'sbwsclient'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorStream(relay, circ, server_host, client_nick, msg=msg)
    d = {
        'msg': msg, 'fingerprint': fp1,
        'nickname': nick, 'address': relay_ip, 'circ': circ,
        'server_host': server_host, 'scanner': client_nick,
        'version': res_proto_ver, 'type': _ResultType.ErrorStream, 'time': t,
    }
    r2 = Result.from_dict(d)
    assert isinstance(r1, ResultErrorStream)
    assert isinstance(r2, ResultErrorStream)
    assert str(r1) == str(r2)


@patch('sbws.lib.resultdump.time_now')
def test_ResultErrorAuth(time_now):
    t = 2000
    time_now.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    circ = [fp1, fp2]
    server_host = '::1'
    client_nick = 'sbwsclient'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorAuth(relay, circ, server_host, client_nick, msg=msg)
    r2 = ResultErrorAuth(relay, circ, server_host, client_nick, msg=msg,
                         t=t)
    assert r1.msg == msg
    assert r1.nickname == nick
    assert r1.time == t
    assert r1.fingerprint == fp1
    assert r1.scanner == client_nick
    assert r1.type == _ResultType.ErrorAuth
    assert r1.address == relay_ip
    assert r1.circ == circ
    assert r1.server_host == server_host
    assert r1.version == res_proto_ver
    assert str(r1) == str(r2)


@patch('sbws.lib.resultdump.time_now')
def test_ResultErrorAuth_from_dict(time_now):
    t = 2000
    time_now.side_effect = monotonic_time(start=t)
    fp1 = 'A' * 40
    fp2 = 'Z' * 40
    circ = [fp1, fp2]
    server_host = '::1'
    client_nick = 'sbwsclient'
    nick = 'Mooooooo'
    relay_ip = '169.254.100.1'
    relay = Result.Relay(fp1, nick, relay_ip)
    msg = 'aaaaayyyyyy bb'
    r1 = ResultErrorAuth(relay, circ, server_host, client_nick, msg=msg)
    d = {
        'msg': msg, 'fingerprint': fp1,
        'nickname': nick, 'address': relay_ip, 'circ': circ,
        'server_host': server_host, 'scanner': client_nick,
        'version': res_proto_ver, 'type': _ResultType.ErrorAuth, 'time': t,
    }
    r2 = Result.from_dict(d)
    assert isinstance(r1, ResultErrorAuth)
    assert isinstance(r2, ResultErrorAuth)
    assert str(r1) == str(r2)
