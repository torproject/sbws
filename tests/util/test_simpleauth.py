from sbws.util.simpleauth import authenticate_client
from sbws.util.simpleauth import authenticate_to_server
from sbws.util.simpleauth import (MAGIC_BYTES, PW_LEN, SUCCESS_BYTES)
from sbws import wire_proto_ver
from configparser import ConfigParser
import socket


class MockServerSideSocket(socket.socket):
    def __init__(self, data):
        assert isinstance(data, bytes)
        self._data = data
        self._next = 0
        self._sent_data = b''

    def recv(self, amount):
        assert isinstance(amount, int)
        start = self._next
        end = start + amount
        ret = self._data[start:end]
        self._next += len(ret)
        return ret

    def send(self, b):
        assert isinstance(b, bytes)
        self._sent_data += b

    def testing_get_sent_data(self):
        return self._sent_data

    def fileno(self):
        return 42


class MockServerSideSocketTimeout(socket.socket):
    def __init__(self):
        pass

    def recv(self, amount):
        raise socket.timeout('timeoutmock')

    def fileno(self):
        return 42


class MockServerSideSocketDelayedTimeout(socket.socket):
    def __init__(self, data):
        assert isinstance(data, bytes)
        self._data = data
        self._next = 0

    def recv(self, amount):
        assert isinstance(amount, int)
        start = self._next
        if start >= len(self._data):
            raise socket.timeout('timeoutmock')
        end = start + amount
        if end > len(self._data):
            raise socket.timeout('timeoutmock')
        ret = self._data[start:end]
        self._next += len(ret)
        return ret

    def fileno(self):
        return 42


class MockServerSideSocketTimeoutOnSend(MockServerSideSocket):
    def send(self, b):
        raise socket.timeout('timeoutmock')


server_conf = ConfigParser()
server_conf.read_dict({
    'server.passwords': {
        'client1': 'a' * PW_LEN,
        'client2': 'b' * PW_LEN,
    },
})


def test_simpleauth_authclient_nodata(capsys):
    in_data = b''
    sock = MockServerSideSocket(in_data)
    ret = authenticate_client(sock, server_conf['server.passwords'])
    captured = capsys.readouterr()
    assert captured.out == 'Magic string doesn\'t match\n'
    assert ret is None


def test_simpleauth_authclient_timeout_magic(capsys):
    sock = MockServerSideSocketTimeout()
    ret = authenticate_client(sock, server_conf['server.passwords'])
    captured = capsys.readouterr()
    assert ret is None
    assert captured.out == 'timeoutmock\n'


def test_simpleauth_authclient_goodmagic(capsys):
    in_data = MAGIC_BYTES
    sock = MockServerSideSocket(in_data)
    ret = authenticate_client(sock, server_conf['server.passwords'])
    assert ret is None
    captured = capsys.readouterr()
    lines = captured.out.strip().split('\n')
    for line in lines:
        if 'Client gave protocol version None but we support' in line:
            break
    else:
        assert None, 'Couldn\'t find output indicating auth failure'


def test_simpleauth_authclient_timeout_version(capsys):
    in_data = MAGIC_BYTES
    sock = MockServerSideSocketDelayedTimeout(in_data)
    ret = authenticate_client(sock, server_conf['server.passwords'])
    captured = capsys.readouterr()
    assert ret is None
    assert 'timeoutmock' in captured.out  # Gets logged in read_line
    assert 'Client gave protocol version None but we support' in captured.out


def test_simpleauth_authclient_goodversion(capsys):
    in_data = MAGIC_BYTES + bytes(str(wire_proto_ver), 'utf-8') + b'\n'
    sock = MockServerSideSocket(in_data)
    ret = authenticate_client(sock, server_conf['server.passwords'])
    assert ret is None
    captured = capsys.readouterr()
    assert captured.out == 'Invalid password\n'


def test_simpleauth_authclient_nonunicodepassword(capsys):
    in_data = MAGIC_BYTES + bytes(str(wire_proto_ver), 'utf-8') + b'\n'
    in_data += b'\x80' * PW_LEN
    sock = MockServerSideSocket(in_data)
    ret = authenticate_client(sock, server_conf['server.passwords'])
    assert ret is None
    captured = capsys.readouterr()
    assert captured.out == 'Non-unicode password string received\n'


def test_simpleauth_authclient_timeout_password(capsys):
    in_data = MAGIC_BYTES + bytes(str(wire_proto_ver), 'utf-8') + b'\n'
    in_data += b'a' * (PW_LEN - 1)
    sock = MockServerSideSocketDelayedTimeout(in_data)
    ret = authenticate_client(sock, server_conf['server.passwords'])
    assert ret is None
    captured = capsys.readouterr()
    assert captured.out == 'timeoutmock\n'


def test_simpleauth_authclient_badpassword(capsys):
    in_data = MAGIC_BYTES + bytes(str(wire_proto_ver), 'utf-8') + b'\n'
    in_data += b'c' * PW_LEN
    sock = MockServerSideSocket(in_data)
    ret = authenticate_client(sock, server_conf['server.passwords'])
    assert ret is None
    captured = capsys.readouterr()
    assert captured.out == 'Invalid password\n'


def test_simpleauth_authclient_goodpassword(capsys):
    in_data = MAGIC_BYTES + bytes(str(wire_proto_ver), 'utf-8') + b'\n'
    in_data += b'a' * PW_LEN
    sock = MockServerSideSocket(in_data)
    ret = authenticate_client(sock, server_conf['server.passwords'])
    assert ret == 'client1'
    captured = capsys.readouterr()
    assert captured.out == ''
    assert sock.testing_get_sent_data() == SUCCESS_BYTES


def test_simpleauth_authclient_cantsend(capsys):
    in_data = MAGIC_BYTES + bytes(str(wire_proto_ver), 'utf-8') + b'\n'
    in_data += b'a' * PW_LEN
    sock = MockServerSideSocketTimeoutOnSend(in_data)
    ret = authenticate_client(sock, server_conf['server.passwords'])
    assert ret is None
    captured = capsys.readouterr()
    assert captured.out == 'timeoutmock\n'


class MockClientSideSocket(socket.socket):
    allowed_password = 'a' * PW_LEN

    def __init__(self):
        self._sent_data = b''

    def send(self, d):
        self._sent_data += d

    def testing_get_sent_data(self):
        return self._sent_data

    def recv(self, amount):
        assert isinstance(amount, int)
        correct_sent_data = MAGIC_BYTES + bytes(str(wire_proto_ver), 'utf-8') \
            + b'\n' + bytes(MockClientSideSocket.allowed_password, 'utf-8')
        if self.testing_get_sent_data() != correct_sent_data:
            raise ConnectionResetError('connresetmock')
        return SUCCESS_BYTES

    def fileno(self):
        return 42


class MockClientSideSocketTimeout(MockClientSideSocket):
    def send(self, d):
        raise socket.timeout('timeoutmock')


class MockClientSideSocketWrongSuccessCode(MockClientSideSocket):
    def recv(self, amount):
        assert isinstance(amount, int)
        correct_sent_data = MAGIC_BYTES + bytes(str(wire_proto_ver), 'utf-8') \
            + b'\n' + bytes(MockClientSideSocket.allowed_password, 'utf-8')
        if self.testing_get_sent_data() != correct_sent_data:
            raise ConnectionResetError('connresetmock')
        assert b'!' != SUCCESS_BYTES, 'SUCCESS_BYTES changed and this mock '\
            'needs to be updated'
        return b'!'


def test_simpleauth_authserver_timeout(capsys):
    sock = MockClientSideSocketTimeout()
    pw = 'a' * PW_LEN
    ret = authenticate_to_server(sock, pw)
    assert ret is False
    captured = capsys.readouterr()
    assert captured.out == 'timeoutmock\n'


def test_simpleauth_authserver_bad(capsys):
    sock = MockClientSideSocket()
    pw = 'b' * 64
    ret = authenticate_to_server(sock, pw)
    assert ret is False
    captured = capsys.readouterr()
    assert captured.out == 'connresetmock\n'


def test_simpleauth_authserver_good(capsys):
    sock = MockClientSideSocket()
    pw = 'a' * 64
    ret = authenticate_to_server(sock, pw)
    assert ret is True


def test_simpleauth_authserver_badsuccesscode(capsys):
    sock = MockClientSideSocketWrongSuccessCode()
    pw = 'a' * 64
    ret = authenticate_to_server(sock, pw)
    assert ret is False
    captured = capsys.readouterr()
    assert captured.out == 'Didn\'t get success code from server\n'
