import os
import socket

MAGIC_BYTES = b'SBWS'
SUCCESS_BYTES = b'1'
PW_LEN = 64


def authenticate_client(sock, pw_file, log_fn=print):
    ''' Use this on the server side to read bytes from the client and properly
    authenticate them. Return True if the client checks out, otherwise False.
    '''
    assert sock.fileno() > 0
    assert is_good_serverside_password_file(pw_file)
    try:
        magic = sock.recv(len(MAGIC_BYTES))
    except socket.timeout as e:
        log_fn(e)
        return False
    if magic != MAGIC_BYTES:
        log_fn('Magic string doesn\'t match')
        return False

    try:
        pw = str(sock.recv(PW_LEN), 'utf-8')
    except UnicodeDecodeError:
        log_fn('Non-unicode password string received')
        return False
    except socket.timeout as e:
        log_fn(e)
        return False

    if not _is_valid_password(pw, pw_file):
        log_fn('Invalid password')
        return False

    try:
        sock.send(SUCCESS_BYTES)
    except (ConnectionResetError, BrokenPipeError) as e:
        log_fn(e)
        return False
    return True


def authenticate_to_server(sock, pw_file, log_fn=print):
    ''' Use this on the client side to send bytes to the server and properly
    authenticate to them. Returns True if successful, otherwise False '''
    assert sock.fileno() > 0
    pw = _get_client_password(pw_file)
    try:
        sock.send(MAGIC_BYTES)
        sock.send(bytes(pw, 'utf-8'))
        msg = sock.recv(len(SUCCESS_BYTES))
    except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
        log_fn(e)
        return False
    if msg != SUCCESS_BYTES:
        log_fn('Didn\'t get success code from server')
        return False
    return True


def is_good_clientside_password_file(pw_file):
    ''' Returns True if the file exists and the first line of the file is a
    valid password character string. Otherwise return False and reason
    string '''
    if not os.path.isfile(pw_file):
        return False, '{} does not exist'.format(pw_file)
    with open(pw_file, 'rt') as fd:
        for line in fd:
            if line[0] == '#':
                continue
            if len(line) != PW_LEN + 1:
                return False, 'Password must be on first line and {} chars '\
                    'long'.format(PW_LEN)
            return True, ''


def is_good_serverside_password_file(pw_file):
    ''' Returns True if all the lines in the file are PW_LEN chars long.
    Otherwise returns False and reason string '''
    if not os.path.isfile(pw_file):
        return False, '{} does not exist'.format(pw_file)
    has_a_line = False
    with open(pw_file, 'rt') as fd:
        for i, line in enumerate(fd):
            if line[0] == '#':
                continue
            has_a_line = True
            if len(line) != PW_LEN + 1:
                return False, 'Line #{} is not {} chars long'.format(i, PW_LEN)
    if not has_a_line:
        return False, 'File must have at least one line'
    return True, ''


def _is_valid_password(pw, pw_file):
    assert is_good_serverside_password_file(pw_file)
    with open(pw_file, 'rt') as fd:
        for line in fd:
            if line[0] == '#':
                continue
            line = line[0:-1]
            if pw == line:
                return True
    return False


def _get_client_password(pw_file):
    assert is_good_clientside_password_file(pw_file)
    with open(pw_file, 'rt') as fd:
        for line in fd:
            if line[0] == '#':
                continue
            return line[0:-1]
