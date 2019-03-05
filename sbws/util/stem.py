import socks

from stem.control import (Controller, Listener)
from stem import (SocketError, InvalidRequest, UnsatisfiableRequest,
                  OperationFailed, ControllerError, InvalidArguments,
                  ProtocolError, SocketClosed)
from stem.connection import IncorrectSocketType
import stem.process
from configparser import ConfigParser
from threading import RLock
import copy
import logging
import os
from sbws.globals import fail_hard
from sbws.globals import (TORRC_STARTING_POINT, TORRC_RUNTIME_OPTIONS,
                          TORRC_OPTIONS_CAN_FAIL)
from sbws import settings

log = logging.getLogger(__name__)
stream_building_lock = RLock()


def attach_stream_to_circuit_listener(controller, circ_id):
    ''' Returns a function that should be given to add_event_listener(). It
    looks for newly created streams and attaches them to the given circ_id '''

    def closure_stream_event_listener(st):
        if st.status == 'NEW' and st.purpose == 'USER':
            log.debug('Attaching stream %s to circ %s %s', st.id, circ_id,
                      circuit_str(controller, circ_id))
            try:
                controller.attach_stream(st.id, circ_id)
            except (UnsatisfiableRequest, InvalidRequest) as e:
                log.warning('Couldn\'t attach stream to circ %s: %s',
                            circ_id, e)
            except OperationFailed as e:
                log.exception("Error attaching stream %s to circ %s: %s",
                              st.id, circ_id, e)
        else:
            pass
    return closure_stream_event_listener


def add_event_listener(controller, func, event):
    try:
        controller.add_event_listener(func, event)
    except ProtocolError as e:
        log.exception("Exception trying to add event listener %s", e)


def remove_event_listener(controller, func):
    try:
        controller.remove_event_listener(func)
    except SocketClosed as e:
        if not settings.end_event.is_set():
            log.debug(e)
        else:
            log.exception(e)
    except ProtocolError as e:
        log.exception("Exception trying to remove event %s", e)


def init_controller(port=None, path=None, set_custom_stream_settings=True):
    # NOTE: we do not currently support a control port even though the rest of
    # this function will pretend like port could be set.
    assert port is None
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
        # These options are also set in launch_tor.
        # In a future refactor they could be set in the case they are not
        # already in the running instance. This way the controller_port
        # could also be used.
        set_torrc_options_can_fail(c)
        set_torrc_runtime_options(c)
    return c, ''


def is_bootstrapped(c):
    try:
        line = c.get_info('status/bootstrap-phase')
    except (ControllerError, InvalidArguments, ProtocolError) as e:
        log.exception("Error trying to check bootstrap phase %s", e)
        return False
    state, _, progress, *_ = line.split()
    progress = int(progress.split('=')[1])
    if state == 'NOTICE' and progress == 100:
        return True
    log.debug('Not bootstrapped. state={} progress={}'.format(state, progress))
    return False


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
        log.debug("Error initting controller socket: socket error.")
        return None
    except Exception as e:
        log.exception("Error initting controller socket: %s", e)
        return None
    # TODO: Allow for auth via more than just CookieAuthentication
    return c


def parse_user_torrc_config(torrc, torrc_text):
    """Parse the user configuration torrc text call `extra_lines`
    to a dictionary suitable to use with stem and return a new torrc
    dictionary that merges that dictionary with the existing torrc.
    Example:
        [tor]
        extra_lines =
            Log debug file /tmp/tor-debug.log
            NumCPUs 1
    """
    torrc_dict = torrc.copy()
    for line in torrc_text.split('\n'):
        # Remove leading and trailing whitespace, if any
        line = line.strip()
        # Ignore blank lines
        if len(line) < 1:
            continue
        # Some torrc options are only a key, some are a key value pair.
        kv = line.split(None, 1)
        if len(kv) > 1:
            key, value = kv
        else:
            key = kv[0]
            value = None
        # It's really easy to add to the torrc if the key doesn't exist
        if key not in torrc:
            torrc_dict.update({key: value})
        # But if it does, we have to make a list of values. For example, say
        # the user wants to add a SocksPort and we already have
        # 'SocksPort auto' in the torrc. We'll go from
        #     torrc['SocksPort'] == 'auto'
        # to
        #     torrc['SocksPort'] == ['auto', '9050']
        else:
            existing_val = torrc[key]
            if isinstance(existing_val, str):
                torrc_dict.update({key: [existing_val, value]})
            else:
                assert isinstance(existing_val, list)
                existing_val.append(value)
                torrc_dict.update({key: existing_val})
        log.debug('Adding "%s %s" to torrc with which we are launching Tor',
                  key, value)
    return torrc_dict


def set_torrc_runtime_options(controller):
    """Set torrc options at runtime."""
    try:
        controller.set_options(TORRC_RUNTIME_OPTIONS)
    # Only the first option that fails will be logged here.
    # Just log stem's exceptions.
    except (ControllerError, InvalidRequest, InvalidArguments) as e:
        log.exception(e)
        exit(1)


def set_torrc_options_can_fail(controller):
    """Set options that can fail, at runtime.

    They can be set at launch, but since the may fail because they are not
    supported in some Tor versions, it's easier to try one by one at runtime
    and ignore the ones that fail.
    """
    for k, v in TORRC_OPTIONS_CAN_FAIL.items():
        try:
            controller.set_conf(k, v)
        except InvalidArguments as error:
            log.debug('Ignoring option not supported by this Tor version. %s',
                      error)


def launch_tor(conf):
    assert isinstance(conf, ConfigParser)
    os.makedirs(conf.getpath('tor', 'datadir'), mode=0o700, exist_ok=True)
    os.makedirs(conf.getpath('tor', 'log'), exist_ok=True)
    os.makedirs(conf.getpath('tor', 'run_dpath'), mode=0o700, exist_ok=True)
    # Bare minimum things, more or less
    torrc = copy.deepcopy(TORRC_STARTING_POINT)
    # Very important and/or common settings that we don't know until runtime
    # The rest of the settings are in globals.py
    torrc.update({
        'DataDirectory': conf.getpath('tor', 'datadir'),
        'PidFile': conf.getpath('tor', 'pid'),
        'ControlSocket': conf.getpath('tor', 'control_socket'),
        'Log': [
            'NOTICE file {}'.format(os.path.join(conf.getpath('tor', 'log'),
                                                 'notice.log')),
        ],
        # Things needed to make circuits fail a little faster. We get the
        # circuit_timeout as a string instead of an int on purpose: stem only
        # accepts strings.
        'LearnCircuitBuildTimeout': '0',
        'CircuitBuildTimeout': conf['general']['circuit_timeout'],
    })

    torrc = parse_user_torrc_config(torrc, conf['tor']['extra_lines'])
    # Finally launch Tor
    try:
        stem.process.launch_tor_with_config(
            torrc, init_msg_handler=log.debug, take_ownership=True)
    except Exception as e:
        fail_hard('Error trying to launch tor: %s', e)
    # And return a controller to it
    cont = _init_controller_socket(conf.getpath('tor', 'control_socket'))
    # Set options that can fail at runtime
    set_torrc_options_can_fail(cont)
    # Set runtime options
    set_torrc_runtime_options(cont)

    log.info('Started and connected to Tor %s via %s', cont.get_version(),
             conf.getpath('tor', 'control_socket'))
    return cont


def get_socks_info(controller):
    ''' Returns the first SocksPort Tor is configured to listen on, in the form
    of an (address, port) tuple '''
    try:
        socks_ports = controller.get_listeners(Listener.SOCKS)
        return socks_ports[0]
    except SocketClosed as e:
        if not settings.end_event.is_set():
            log.debug(e)
    # This might need to return the eception if this happen in other cases
    # than when stopping the scanner.
    except ControllerError as e:
        log.debug(e)


def only_relays_with_bandwidth(controller, relays, min_bw=None, max_bw=None):
    '''
    Given a list of relays, only return those that optionally have above
    **min_bw** and optionally have below **max_bw**, inclusively. If neither
    min_bw nor max_bw are given, essentially just returns the input list of
    relays.
    '''
    assert min_bw is None or min_bw >= 0
    assert max_bw is None or max_bw >= 0
    ret = []
    for relay in relays:
        assert hasattr(relay, 'consensus_bandwidth')
        if min_bw is not None and relay.consensus_bandwidth < min_bw:
            continue
        if max_bw is not None and relay.consensus_bandwidth > max_bw:
            continue
        ret.append(relay)
    return ret


def circuit_str(controller, circ_id):
    assert isinstance(circ_id, str)
    int(circ_id)
    try:
        circ = controller.get_circuit(circ_id)
    except ValueError as e:
        log.warning('Circuit %s no longer seems to exist so can\'t return '
                    'a valid circuit string for it: %s', circ_id, e)
        return None
    # exceptions raised when stopping the scanner
    except (ControllerError, SocketClosed, socks.GeneralProxyError) as e:
        log.debug(e)
        return None
    return '[' +\
        ' -> '.join(['{} ({})'.format(n, fp[0:8]) for fp, n in circ.path]) +\
        ']'
