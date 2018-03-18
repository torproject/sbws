from stem.control import Controller
from stem import (SocketError, InvalidRequest, UnsatisfiableRequest)

__all__ = [
    'add_event_listener',
    'remove_event_listener',
    'attach_stream_to_circuit_listener',
    'init_controller',
    'is_controller_okay',
]

DEFAULT_ATTEMPTS = [
    ('socket', '/home/matt/src/chutney/net/nodes/009c/control'),
    ('socket', '/home/ubuntu/src/chutney/net/nodes/009c/control'),
    ('socket', '/var/run/tor/control'),
    ('port', 9051),
    ('port', 9151),
]


def attach_stream_to_circuit_listener(controller, circ_id):
    assert is_controller_okay(controller)
    def closure_stream_event_listener(st):
        if st.status == 'NEW' and st.purpose == 'USER':
            print('Attaching stream {} to circ {}'.format(st.id, circ_id))
            try:
                controller.attach_stream(st.id, circ_id)
            except (UnsatisfiableRequest, InvalidRequest) as e:
                print('Couldn\'t attach stream to circ {}: {}'.format(circ_id, e))
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


def init_controller(set_custom_stream_settings=True):
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
