from ..util.sockio import read_line
import socket

MAGIC_BYTES = b'SBWS'
SUCCESS_BYTES = b'.'
PW_LEN = 64
PROTO_VER = b'1'


def authenticate_client(sock, passwords, log_fn=print):
    ''' Use this on the server side to read bytes from the client and properly
    authenticate them. Return True if the client checks out, otherwise False.
    '''
    assert sock.fileno() > 0
    assert isinstance(passwords, list)
    assert len(passwords) > 0
    try:
        magic = sock.recv(len(MAGIC_BYTES))
    except socket.timeout as e:
        log_fn(e)
        return False
    if magic != MAGIC_BYTES:
        log_fn('Magic string doesn\'t match')
        return False

    try:
        line = read_line(sock, max_len=4, log_fn=log_fn)
    except socket.timeout as e:
        log_fn(e)
        return False
    if line != str(PROTO_VER, 'utf-8'):
        log_fn('Client gave protocol version {} but we support {}'.format(
            line, str(PROTO_VER, 'utf-8')))
        return False

    try:
        pw = str(sock.recv(PW_LEN), 'utf-8')
    except UnicodeDecodeError:
        log_fn('Non-unicode password string received')
        return False
    except socket.timeout as e:
        log_fn(e)
        return False

    if not _is_valid_password(pw, passwords):
        log_fn('Invalid password')
        return False

    try:
        sock.send(SUCCESS_BYTES)
    except (ConnectionResetError, BrokenPipeError) as e:
        log_fn(e)
        return False
    return True


def authenticate_to_server(sock, pw, log_fn=print):
    ''' Use this on the client side to send bytes to the server and properly
    authenticate to them. Returns True if successful, otherwise False '''
    assert sock.fileno() > 0
    assert isinstance(pw, str)
    assert len(pw) == PW_LEN
    try:
        sock.send(MAGIC_BYTES)
        sock.send(PROTO_VER + b'\n')
        sock.send(bytes(pw, 'utf-8'))
        msg = sock.recv(len(SUCCESS_BYTES))
    except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
        log_fn(e)
        return False
    if msg != SUCCESS_BYTES:
        log_fn('Didn\'t get success code from server')
        return False
    return True


def _is_valid_password(pw, passwords):
    assert isinstance(passwords, list)
    assert len(passwords) > 0
    if len(pw) == PW_LEN and pw in passwords:
        return True
    return False
