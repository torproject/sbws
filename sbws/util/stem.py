from stem.control import Controller
from stem import (SocketError, InvalidRequest, UnsatisfiableRequest)
from stem.connection import IncorrectSocketType

__all__ = [
    'add_event_listener',
    'remove_event_listener',
    'attach_stream_to_circuit_listener',
    'init_controller',
    'is_controller_okay',
    'fp_or_nick_to_relay',
]


def fp_or_nick_to_relay(controller, fp_nick):
    ''' Takes a string that could be either a relay's fingerprint or nickname.
    Return the relay's descriptor if found. Otherwise return None.

    Note that if a nickname is given and multiple relays have that nickname,
    only one of them will be returned. '''
    assert isinstance(fp_nick, str)
    assert is_controller_okay(controller)
    return controller.get_network_status(fp_nick, default=None)


def attach_stream_to_circuit_listener(controller, circ_id, log_fn=print):
    ''' Returns a function that should be given to add_event_listener(). It
    looks for newly created streams and attaches them to the given circ_id '''
    assert is_controller_okay(controller)

    def closure_stream_event_listener(st):
        if st.status == 'NEW' and st.purpose == 'USER':
            log_fn('Attaching stream {} to circ {}'.format(st.id, circ_id))
            try:
                controller.attach_stream(st.id, circ_id)
            except (UnsatisfiableRequest, InvalidRequest) as e:
                log_fn('Couldn\'t attach stream to circ {}:'.format(circ_id),
                       e)
        else:
            pass
    return closure_stream_event_listener


def add_event_listener(controller, func, event):
    assert is_controller_okay(controller)
    controller.add_event_listener(func, event)


def remove_event_listener(controller, func, log_fn=print):
    if not is_controller_okay(controller):
        log_fn('Warning: controller not okay so not trying to remove event')
        return
    controller.remove_event_listener(func)


def init_controller(port=None, path=None, set_custom_stream_settings=True,
                    log_fn=print):
    # make sure only one is set
    assert port is not None or path is not None
    assert not (port is not None and path is not None)
    # and for the one that is set, make sure it is likely valid
    assert port is None or isinstance(port, int)
    assert path is None or isinstance(path, str)
    c = None
    if port:
        c = _init_controller_port(port)
        if not c:
            log_fn('Unable to reach tor on control port', port)
            return None
    else:
        c = _init_controller_socket(path)
        if not c:
            log_fn('Unable to reach tor on control socket', path)
            return None
    assert c is not None
    log_fn('Connected to Tor via', port if port else path)
    if set_custom_stream_settings:
        c.set_conf('__DisablePredictedCircuits', '1')
        c.set_conf('__LeaveStreamsUnattached', '1')
    return c


def is_controller_okay(c):
    if not c:
        return False
    return c.is_alive() and c.is_authenticated()


def _init_controller_port(port):
    assert isinstance(port, int)
    try:
        c = Controller.from_port(port=port)
        c.authenticate()
    except (IncorrectSocketType, SocketError):
        return None
    # TODO: Allow for auth via more than just CookieAuthentication
    return c


def _init_controller_socket(socket):
    assert isinstance(socket, str)
    try:
        c = Controller.from_socket_file(path=socket)
        c.authenticate()
    except (IncorrectSocketType, SocketError):
        return None
    # TODO: Allow for auth via more than just CookieAuthentication
    return c
