from sbws.globals import SOCKET_TIMEOUT
import socket
import socks
import logging

log = logging.getLogger(__name__)


def read_line(s, max_len=None):
    '''
    Read from the blocking socket **s** until nothing can be read anymore or
    until a b'\n' is seen.

    If max_len is specified, then that's the maximum number of characters that
    will be returned, even if a newline is not read yet.

    This function can only handle characters that can be represented as a
    single byte in utf8.

    :param socket.socket s: Blocking socket to read from
    :param int max_len: Maximum number of bytes to read, not including a
        tailing newline
    :raises UnicodeDecodeError: If any byte is not a valid utf8 byte
    :returns: Everything read up until a newline as a str and with a maximum
        length of **max_len**. If nothing could be read, returns None. If a
        newline is the first character, returns an empty str.
    '''
    assert isinstance(s, socket.socket)
    assert max_len is None or (isinstance(max_len, int) and max_len > 0)
    chars = None
    while True:
        try:
            c = s.recv(1)
        except (ConnectionResetError, BrokenPipeError, socket.timeout) as e:
            log.warning(e)
            return None
        if not c:
            return chars
        if chars is None:
            chars = ''
        if c == b'\n':
            break
        try:
            chars += c.decode('utf-8')
        except UnicodeDecodeError as e:
            raise e
        if max_len is not None and len(chars) >= max_len:
            return chars[0:max_len]
    return chars


def make_socket(socks_host, socks_port):
    '''
    Make a socket that uses the provided socks5 proxy. Note at this point
    the socket hasn't ``connect()``ed anywhere.

    :param str socks_host: IP address or hostname of the socks5 proxy to use
    :param int socks_port: Port of the socks5 proxy to use
    :returns: A socket ready to ``connect()`` somewhere
    '''
    s = socks.socksocket()
    s.set_proxy(socks.PROXY_TYPE_SOCKS5, socks_host, socks_port)
    s.settimeout(SOCKET_TIMEOUT)
    return s


def close_socket(s):
    ''' Close the socket, and ignore any errors. '''
    try:
        s.shutdown(socket.SHUT_RDWR)
        s.close()
    except Exception:
        pass


def socket_connect(s, addr, port):
    '''
    ``connect()`` to addr:port on the given socket. **addr** can be a hostname,
    IPv4, or IPv6 address.

    :param socket s: Socket, possibly through a socks5 proxy
    :param str addr: host to connect to
    :param int port: port to connect to
    :returns: True if connect was successful, otherwise False.
    '''
    try:
        s.connect((addr, port))
        log.debug('Connected to %s:%d via %d', addr, port, s.fileno())
    except (socket.timeout, socks.GeneralProxyError,
            socks.ProxyConnectionError) as e:
        log.warning(e)
        return False
    return True
