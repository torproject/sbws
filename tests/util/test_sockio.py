from sbws.util.sockio import read_line
import socket


class MockReadingSocket(socket.socket):
    def __init__(self, data):
        assert isinstance(data, bytes)
        self._data = data
        self._next = 0

    def recv(self, amount):
        assert amount == 1, 'read_line should only ever request one byte'
        start = self._next
        end = start + amount
        ret = self._data[start:end]
        self._next += len(ret)
        return ret


class MockReadingSocketWithTimeout(socket.socket):
    def __init__(self):
        pass

    def recv(self, amount):
        raise socket.timeout()


def test_sockio_simple():
    in_str = b'1234\n'
    expected = '1234'
    sock = MockReadingSocket(in_str)
    out = read_line(sock)
    assert out == expected


def test_sockio_empty():
    in_str = b'\n'
    expected = ''
    sock = MockReadingSocket(in_str)
    out = read_line(sock)
    assert out == expected


def test_sockio_null():
    in_str = b''
    expected = None
    sock = MockReadingSocket(in_str)
    out = read_line(sock)
    assert out == expected


def test_sockio_too_much():
    in_str = b'12345678\n'
    expected = '1234'
    sock = MockReadingSocket(in_str)
    out = read_line(sock, max_len=len(expected))
    assert out == expected


def test_sockio_timeout():
    expected = None
    sock = MockReadingSocketWithTimeout()
    try:
        out = read_line(sock)
    except socket.timeout:
        assert None, 'Should not have let the timeout bubble up'
    assert out == expected


def test_sockio_missing_newline():
    in_str = b'1234'
    expected = '1234'
    sock = MockReadingSocket(in_str)
    out = read_line(sock)
    assert out == expected


def test_sockio_bad_max_len():
    in_str = b'1234'
    sock = MockReadingSocket(in_str)
    try:
        read_line(sock, max_len=1.2)
    except AssertionError:
        pass
    else:
        assert None, 'Should have failed'


def test_sockio_non_ascii():
    in_str = b'asdf\x80asdf'
    sock = MockReadingSocket(in_str)
    try:
        read_line(sock)
    except UnicodeDecodeError:
        pass
    else:
        assert None, 'Should have failed'
