from stem.control import (Controller, EventType)
from stem import (SocketError, InvalidRequest, UnsatisfiableRequest)
from stem.connection import IncorrectSocketType
import stem.process
from configparser import ConfigParser
from threading import RLock
import logging
import os
from sbws.util.sockio import socket_connect
from sbws.globals import fail_hard

log = logging.getLogger(__name__)

stream_building_lock = RLock()

__all__ = [
    'add_event_listener',
    'remove_event_listener',
    'attach_stream_to_circuit_listener',
    'init_controller',
    'init_controller_with_config',
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


def attach_stream_to_circuit_listener(controller, circ_id):
    ''' Returns a function that should be given to add_event_listener(). It
    looks for newly created streams and attaches them to the given circ_id '''
    assert is_controller_okay(controller)

    def closure_stream_event_listener(st):
        if st.status == 'NEW' and st.purpose == 'USER':
            log.debug('Attaching stream %s to circ %s', st.id, circ_id)
            try:
                controller.attach_stream(st.id, circ_id)
            except (UnsatisfiableRequest, InvalidRequest) as e:
                log.warning('Couldn\'t attach stream to circ %s: %s',
                            circ_id, e)
        else:
            pass
    return closure_stream_event_listener


def add_event_listener(controller, func, event):
    assert is_controller_okay(controller)
    controller.add_event_listener(func, event)


def remove_event_listener(controller, func):
    if not is_controller_okay(controller):
        log.warning('Controller not okay so not trying to remove event')
        return
    controller.remove_event_listener(func)


def connect_over_circuit(controller, circ_id, sock, host, port):
    with stream_building_lock:
        listener = attach_stream_to_circuit_listener(controller, circ_id)
        add_event_listener(controller, listener, EventType.STREAM)
        connected = socket_connect(sock, host, port)
        remove_event_listener(controller, listener)
    return connected


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
            return None, 'Unable to reach tor on control port'
    else:
        c = _init_controller_socket(path)
        if not c:
            return None, 'Unable to reach tor on control socket'
    assert c is not None
    if set_custom_stream_settings:
        c.set_conf('__DisablePredictedCircuits', '1')
        c.set_conf('__LeaveStreamsUnattached', '1')
    return c, ''


def init_controller_with_config(conf):
    assert isinstance(conf, ConfigParser)
    if conf['tor']['control_type'] not in ['port', 'socket']:
        return None, 'control_type in config must be either port or socket'
    if conf['tor']['control_type'] == 'port':
        try:
            port = conf.getint('tor', 'control_location')
        except ValueError:
            return None, 'control_location must be int if control_type = port'
        c, error_msg = init_controller(port=port)
        if not c:
            return None, error_msg
        return c, ''
    c, error_msg = init_controller(path=conf['tor']['control_location'])
    if not c:
        return None, error_msg
    return c, ''


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


def launch_tor(conf):
    assert isinstance(conf, ConfigParser)
    section = conf['tor']
    os.makedirs(section['datadir'], mode=0o700, exist_ok=True)
    # Bare minimum things, more or less
    c = {
        'SocksPort': 'auto',
        'DataDirectory': section['datadir'],
        'PidFile': os.path.join(section['datadir'], 'tor.pid'),
        'ControlSocket': section['control_socket'],
        'CookieAuthentication': '1',
        'Log': [
            'NOTICE file {}'.format(section['log']),
        ],
    }
    # Things needed to have all the descriptor information we need
    c.update({
        'FetchDirInfoEarly': '1',
        'FetchDirInfoExtraEarly': '1',
        'FetchUselessDescriptors': '1',
        'UseMicrodescriptors': '0',
        'DownloadExtraInfo': '1',
    })
    # Things needed to make circuits fail a little faster
    c.update({
        'LearnCircuitBuildTimeout': '0',
        'CircuitBuildTimeout': '10',
    })
    for line in section['extra_lines'].split('\n'):
        line = line.strip()
        if len(line) < 1:
            continue
        items = line.split()
        if len(items) < 2:
            fail_hard('All torrc lines must have 2 or more words. "%s" has '
                      'fewer', line)
        key, *value = items
        value = ' '.join(value)
        log.info('Adding "%s %s" to torrc with which we are launching Tor',
                 key, value)
        if key in c:
            v = c[key]
            if isinstance(v, str):
                c.update({key: [v, value]})
            else:
                assert isinstance(v, list)
                v.append(value)
                c.update({key: v})
        else:
            c.update({key: value})
    proc = stem.process.launch_tor_with_config(
        c, init_msg_handler=log.debug, take_ownership=True)
    return _init_controller_socket(section['control_socket'])
