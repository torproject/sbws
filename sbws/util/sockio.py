import socket


def read_line(s, max_len=None, log_fn=print):
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
    :param func log_fn: Function with a signature similar to ``print`` to call
        if an error occurs
    :raises UnicodeDecodeError: If any byte is not a valid utf8 byte
    :returns: Everything read up until a newline and with a maximum length of
        **max_len**. If nothing could be read, returns None. If a newline is
        the first character, returns an empty string.
    '''
    assert isinstance(s, socket.socket)
    assert max_len is None or (isinstance(max_len, int) and max_len > 0)
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
        try:
            chars += c.decode('utf-8')
        except UnicodeDecodeError as e:
            raise e
        if max_len is not None and len(chars) >= max_len:
            return chars[0:max_len]
    return chars
