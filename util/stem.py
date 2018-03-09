from stem.control import Controller
from stem import SocketError

__all__ = ['init_controller', 'is_controller_okay']

DEFAULT_ATTEMPTS = [
    ('socket', '/var/run/tor/control'),
    ('port', 9051),
    ('port', 9151),
]


def init_controller():
    for cont_type, cont_location in DEFAULT_ATTEMPTS:
        if cont_type == 'socket':
            c = _init_controller_socket(cont_location)
            if not c:
                continue
        elif cont_type == 'port':
            c = _init_controller_port(cont_location)
            if not c:
                continue
        else:
            raise RuntimeError('Unknown controller type {}'.format(cont_type))
        print('Connected to Tor via', cont_location)
        return c


def is_controller_okay(c):
    if not c:
        return False
    return c.is_alive() and c.is_authenticated()


def _init_controller_port(port):
    assert isinstance(port, int)
    try:
        c = Controller.from_port(port=port)
    except SocketError:
        return None
    # TODO: Allow for auth via more than just CookieAuthentication
    c.authenticate()
    return c


def _init_controller_socket(socket):
    assert isinstance(socket, str)
    try:
        c = Controller.from_socket_file(path=socket)
    except SocketError:
        return None
    # TODO: Allow for auth via more than just CookieAuthentication
    c.authenticate()
    return c
