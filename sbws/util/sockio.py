import socket


def read_line(s, max_len=None, log_fn=print):
    ''' read until b'\n' is seen on the socket <s>. Return everything up until
    the newline as a str. If nothing can be read, return None. Note how that is
    different than if a newline is the first character; in that case, an empty
    str is returned.

    If max_len is specified, then that's the maximum number of characters that
    will be returned, even if a newline is not read yet.
    '''
    assert max_len is None or max_len > 0
    chars = None
    while True:
        try:
            c = s.recv(1)
        except (ConnectionResetError, BrokenPipeError, socket.timeout) as e:
            log_fn(e)
            return None
        if not c:
            return chars
        if chars is None:
            chars = ''
        if c == b'\n':
            break
        chars += c.decode('utf-8')
        if max_len is not None and len(chars) >= max_len:
            return chars[0:max_len]
    return chars
