from ..util.sockio import read_line
import socket
from sbws import wire_proto_ver

MAGIC_BYTES = b'SBWS'
SUCCESS_BYTES = b'.'
PW_LEN = 64


def authenticate_client(sock, conf_section, log_fn=print):
    ''' Use this on the server side to read bytes from the client and properly
    authenticate them. Return the name of the client who has authenticated if
    they provided a good password, otherwise None.
    '''
    assert sock.fileno() > 0
    assert len(conf_section) > 0
    try:
        magic = sock.recv(len(MAGIC_BYTES))
    except socket.timeout as e:
        log_fn(e)
        return None
    if magic != MAGIC_BYTES:
        log_fn('Magic string doesn\'t match')
        return None

    line = read_line(sock, max_len=4, log_fn=log_fn)
    if line != str(wire_proto_ver):
        log_fn('Client gave protocol version {} but we support {}'.format(
            line, wire_proto_ver))
        return None

    try:
        pw = str(sock.recv(PW_LEN), 'utf-8')
    except UnicodeDecodeError:
        log_fn('Non-unicode password string received')
        return None
    except socket.timeout as e:
        log_fn(e)
        return None

    client_name = _is_valid_password(pw, conf_section)
    if not client_name:
        log_fn('Invalid password')
        return None

    try:
        sock.send(SUCCESS_BYTES)
    except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
        log_fn(e)
        return None
    return client_name


def authenticate_to_server(sock, pw, log_fn=print):
    ''' Use this on the client side to send bytes to the server and properly
    authenticate to them. Returns True if successful, otherwise False '''
    assert sock.fileno() > 0
    assert isinstance(pw, str)
    assert len(pw) == PW_LEN
    try:
        sock.send(MAGIC_BYTES)
        sock.send(bytes('{}\n'.format(wire_proto_ver), 'utf-8'))
        sock.send(bytes(pw, 'utf-8'))
        msg = sock.recv(len(SUCCESS_BYTES))
    except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
        log_fn(e)
        return False
    if msg != SUCCESS_BYTES:
        log_fn('Didn\'t get success code from server')
        return False
    return True


def _is_valid_password(pw, conf_section):
    ''' Returns the key in the [server.passwords] section of the config for the
    password the client provided (AKA: if the client provided a valid
    password).  Otherwise return None '''
    assert len(conf_section) > 0
    if len(pw) != PW_LEN:
        return None
    for key in conf_section.keys():
        if pw == conf_section[key]:
            return key
    return False
