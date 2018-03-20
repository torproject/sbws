from stem.control import Controller
from stem import (SocketError, InvalidRequest, UnsatisfiableRequest)

__all__ = [
    'add_event_listener',
    'remove_event_listener',
    'attach_stream_to_circuit_listener',
    'init_controller',
    'is_controller_okay',
]


def attach_stream_to_circuit_listener(controller, circ_id):
    assert is_controller_okay(controller)

    def closure_stream_event_listener(st):
        if st.status == 'NEW' and st.purpose == 'USER':
            print('Attaching stream {} to circ {}'.format(st.id, circ_id))
            try:
                controller.attach_stream(st.id, circ_id)
            except (UnsatisfiableRequest, InvalidRequest) as e:
                print('Couldn\'t attach stream to circ {}:'.format(circ_id), e)
        else:
            pass
    return closure_stream_event_listener


def add_event_listener(controller, func, event):
    assert is_controller_okay(controller)
    controller.add_event_listener(func, event)


def remove_event_listener(controller, func):
    if not is_controller_okay(controller):
        print('Warning: controller not okay so not trying to remove event')
        return
    controller.remove_event_listener(func)


def init_controller(port=None, path=None, set_custom_stream_settings=True):
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
            return None
    else:
        c = _init_controller_socket(path)
        if not c:
            return None
    assert c is not None
    print('Connected to Tor via', port if port else path)
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
