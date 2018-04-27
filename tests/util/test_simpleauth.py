from sbws.util.simpleauth import authenticate_scanner
from sbws.util.simpleauth import authenticate_to_server
from sbws.util.simpleauth import (MAGIC_BYTES, PW_LEN, SUCCESS_BYTES)
from sbws.globals import WIRE_VERSION
from configparser import ConfigParser
import socket
import logging


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
        'scanner1': 'a' * PW_LEN,
        'scanner2': 'b' * PW_LEN,
    },
})


def test_simpleauth_authscanner_nodata(caplog):
    caplog.set_level(logging.DEBUG)
    in_data = b''
    sock = MockServerSideSocket(in_data)
    ret = authenticate_scanner(sock, server_conf['server.passwords'])
    assert len(caplog.records) == 1
    assert 'Magic string doesn\'t match' == caplog.records[0].getMessage()
    assert ret is None


def test_simpleauth_authscanner_timeout_magic(caplog):
    sock = MockServerSideSocketTimeout()
    ret = authenticate_scanner(sock, server_conf['server.passwords'])
    assert ret is None
    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage() == 'timeoutmock'


def test_simpleauth_authscanner_goodmagic(caplog):
    in_data = MAGIC_BYTES
    sock = MockServerSideSocket(in_data)
    ret = authenticate_scanner(sock, server_conf['server.passwords'])
    assert ret is None
    lines = [l.getMessage() for l in caplog.records]
    for line in lines:
        if 'Scanner gave protocol version None but we support' in line:
            break
    else:
        assert None, 'Couldn\'t find output indicating auth failure'


def test_simpleauth_authscanner_timeout_version(caplog):
    in_data = MAGIC_BYTES
    sock = MockServerSideSocketDelayedTimeout(in_data)
    ret = authenticate_scanner(sock, server_conf['server.passwords'])
    assert ret is None
    assert 'timeoutmock' in caplog.text  # Gets logged in read_line
    assert 'Scanner gave protocol version None but we support' in caplog.text


def test_simpleauth_authscanner_goodversion(caplog):
    in_data = MAGIC_BYTES + bytes(str(WIRE_VERSION), 'utf-8') + b'\n'
    sock = MockServerSideSocket(in_data)
    ret = authenticate_scanner(sock, server_conf['server.passwords'])
    assert ret is None
    assert 'Invalid password' in caplog.text


def test_simpleauth_authscanner_nonunicodepassword(caplog):
    in_data = MAGIC_BYTES + bytes(str(WIRE_VERSION), 'utf-8') + b'\n'
    in_data += b'\x80' * PW_LEN
    sock = MockServerSideSocket(in_data)
    ret = authenticate_scanner(sock, server_conf['server.passwords'])
    assert ret is None
    assert 'Non-unicode password string received' in caplog.text


def test_simpleauth_authscanner_timeout_password(caplog):
    in_data = MAGIC_BYTES + bytes(str(WIRE_VERSION), 'utf-8') + b'\n'
    in_data += b'a' * (PW_LEN - 1)
    sock = MockServerSideSocketDelayedTimeout(in_data)
    ret = authenticate_scanner(sock, server_conf['server.passwords'])
    assert ret is None
    assert 'timeoutmock' in caplog.text


def test_simpleauth_authscanner_badpassword(caplog):
    in_data = MAGIC_BYTES + bytes(str(WIRE_VERSION), 'utf-8') + b'\n'
    in_data += b'c' * PW_LEN
    sock = MockServerSideSocket(in_data)
    ret = authenticate_scanner(sock, server_conf['server.passwords'])
    assert ret is None
    assert 'Invalid password' in caplog.text


def test_simpleauth_authscanner_goodpassword(caplog):
    caplog.set_level(logging.DEBUG)
    in_data = MAGIC_BYTES + bytes(str(WIRE_VERSION), 'utf-8') + b'\n'
    in_data += b'a' * PW_LEN
    sock = MockServerSideSocket(in_data)
    ret = authenticate_scanner(sock, server_conf['server.passwords'])
    assert ret == 'scanner1'
    assert len(caplog.records) == 0
    assert sock.testing_get_sent_data() == SUCCESS_BYTES


def test_simpleauth_authscanner_cantsend(caplog):
    in_data = MAGIC_BYTES + bytes(str(WIRE_VERSION), 'utf-8') + b'\n'
    in_data += b'a' * PW_LEN
    sock = MockServerSideSocketTimeoutOnSend(in_data)
    ret = authenticate_scanner(sock, server_conf['server.passwords'])
    assert ret is None
    assert 'timeoutmock' in caplog.text


class MockScannerSideSocket(socket.socket):
    allowed_password = 'a' * PW_LEN

    def __init__(self):
        self._sent_data = b''

    def send(self, d):
        self._sent_data += d

    def testing_get_sent_data(self):
        return self._sent_data

    def recv(self, amount):
        assert isinstance(amount, int)
        correct_sent_data = MAGIC_BYTES + bytes(str(WIRE_VERSION), 'utf-8') \
            + b'\n' + bytes(MockScannerSideSocket.allowed_password, 'utf-8')
        if self.testing_get_sent_data() != correct_sent_data:
            raise ConnectionResetError('connresetmock')
        return SUCCESS_BYTES

    def fileno(self):
        return 42


class MockScannerSideSocketTimeout(MockScannerSideSocket):
    def send(self, d):
        raise socket.timeout('timeoutmock')


class MockScannerSideSocketWrongSuccessCode(MockScannerSideSocket):
    def recv(self, amount):
        assert isinstance(amount, int)
        correct_sent_data = MAGIC_BYTES + bytes(str(WIRE_VERSION), 'utf-8') \
            + b'\n' + bytes(MockScannerSideSocket.allowed_password, 'utf-8')
        if self.testing_get_sent_data() != correct_sent_data:
            raise ConnectionResetError('connresetmock')
        assert b'!' != SUCCESS_BYTES, 'SUCCESS_BYTES changed and this mock '\
            'needs to be updated'
        return b'!'


def test_simpleauth_authserver_timeout(caplog):
    sock = MockScannerSideSocketTimeout()
    pw = 'a' * PW_LEN
    ret = authenticate_to_server(sock, pw)
    assert ret is False
    assert 'timeoutmock' in caplog.text


def test_simpleauth_authserver_bad(caplog):
    sock = MockScannerSideSocket()
    pw = 'b' * 64
    ret = authenticate_to_server(sock, pw)
    assert ret is False
    assert 'connresetmock' in caplog.text


def test_simpleauth_authserver_good():
    sock = MockScannerSideSocket()
    pw = 'a' * 64
    ret = authenticate_to_server(sock, pw)
    assert ret is True


def test_simpleauth_authserver_badsuccesscode(caplog):
    sock = MockScannerSideSocketWrongSuccessCode()
    pw = 'a' * 64
    ret = authenticate_to_server(sock, pw)
    assert ret is False
    assert 'Didn\'t get success code from server' in caplog.text
