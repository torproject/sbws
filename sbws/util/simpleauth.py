from ..util.sockio import read_line
import socket
import logging
from sbws import wire_proto_ver

MAGIC_BYTES = b'SBWS'
SUCCESS_BYTES = b'.'
PW_LEN = 64

log = logging.getLogger(__name__)


def authenticate_scanner(sock, conf_section):
    ''' Use this on the server side to read bytes from the scanner and properly
    authenticate them. Return the name of the scanner who has authenticated if
    they provided a good password, otherwise None.

    :param socket.socket sock: The open and blocking socket to use to
        communicate with the scanner
    :param configparser.SectionProxy conf_section: The ``[server.passwords]``
        section from the sbws config file
    :returns: The name of the scanner that successfully authenticated as a str,
        as pulled from the ``[server.passwords]`` section of the config. If
        the scanner couldn't authenticate, returns None
    '''
    assert sock.fileno() > 0
    assert len(conf_section) > 0
    try:
        magic = sock.recv(len(MAGIC_BYTES))
    except socket.timeout as e:
        log.warning(e)
        return None
    if magic != MAGIC_BYTES:
        log.warning('Magic string doesn\'t match')
        return None

    line = read_line(sock, max_len=4)
    if line != str(wire_proto_ver):
        log.warning('Scanner gave protocol version %s but we support %d', line,
                    wire_proto_ver)
        return None

    try:
        pw = str(sock.recv(PW_LEN), 'utf-8')
    except UnicodeDecodeError:
        log.warning('Non-unicode password string received')
        return None
    except socket.timeout as e:
        log.warning(e)
        return None

    scanner_name = _is_valid_password(pw, conf_section)
    if not scanner_name:
        log.warning('Invalid password')
        return None

    try:
        sock.send(SUCCESS_BYTES)
    except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
        log.warning(e)
        return None
    return scanner_name


def authenticate_to_server(sock, pw):
    '''
    Use this on the server side to send bytes to the server and properly
    authenticate to them.

    :param socket.socket sock: The open and blocking socket to use to
        communicate with the server
    :param str pw: 64 character password string to give to the server for
        identification
    :returns: True if we authenticated to the server successfully, False
        otherwise. On False, the caller should close the socket
    '''
    assert sock.fileno() > 0
    assert isinstance(pw, str)
    assert len(pw) == PW_LEN
    try:
        sock.send(MAGIC_BYTES)
        sock.send(bytes('{}\n'.format(wire_proto_ver), 'utf-8'))
        sock.send(bytes(pw, 'utf-8'))
        msg = sock.recv(len(SUCCESS_BYTES))
    except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
        log.warning(e)
        return False
    if msg != SUCCESS_BYTES:
        log.warning('Didn\'t get success code from server')
        return False
    return True


def _is_valid_password(pw, conf_section):
    ''' Returns the key in the [server.passwords] section of the config for the
    password the scanner provided (AKA: if the scanner provided a valid
    password).  Otherwise return None '''
    assert len(conf_section) > 0
    if len(pw) != PW_LEN:
        return None
    for key in conf_section.keys():
        if pw == conf_section[key]:
            return key
    return False
