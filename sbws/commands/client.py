''' Measure the relays. '''

from ..lib.circuitbuilder import GapsCircuitBuilder as CB
from ..lib.resultdump import ResultDump
from ..lib.resultdump import ResultSuccess
from ..lib.resultdump import ResultErrorCircuit
from ..lib.resultdump import ResultErrorAuth
from ..lib.relaylist import RelayList
from ..lib.relayprioritizer import RelayPrioritizer
from ..lib.helperrelay import HelperRelayList
from ..util.simpleauth import authenticate_to_server
from sbws.globals import (fail_hard, is_initted)
import sbws.util.stem as stem_utils
from stem.control import EventType
from argparse import ArgumentDefaultsHelpFormatter
from multiprocessing.dummy import Pool
from threading import Event
from threading import RLock
import socks
import socket
import time
import os


end_event = Event()
stream_building_lock = RLock()


def make_socket(socks_host, socks_port):
    ''' Make a socket that uses the provided socks5 proxy. Note at this point
    the socket hasn't connect()ed anywhere '''
    s = socks.socksocket()
    s.set_proxy(socks.PROXY_TYPE_SOCKS5, socks_host, socks_port)
    s.settimeout(10)
    return s


def close_socket(s):
    ''' Close the socket, and ignore errors '''
    try:
        s.shutdown(socket.SHUT_RDWR)
        s.close()
    except Exception:
        pass


def socket_connect(s, addr, port):
    ''' connect() to addr:port on the given socket. Unknown compatibility with
    IPv6. Works with IPv4 and hostnames '''
    try:
        s.connect((addr, port))
        log.debug('Connected to', addr, port, 'via', s.fileno())
    except (socket.timeout, socks.GeneralProxyError,
            socks.ProxyConnectionError) as e:
        log.warn(e)
        return False
    return True


def tell_server_amount(sock, expected_amount):
    ''' Returns True on success; else False '''
    assert expected_amount > 0
    # expectd_amount should come in as an int, but we send it to the server as
    # a string (ignore the difference between bytes and str in python. You know
    # what I mean).
    amount = '{}\n'.format(expected_amount)
    try:
        sock.send(bytes(amount, 'utf-8'))
    except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
        log.info(e)
        return False
    return True


def timed_recv_from_server(sock, conf, yet_to_read):
    ''' Return the time in seconds it took to read <yet_to_read> bytes from
    the server. Return None if error '''
    assert yet_to_read > 0
    start_time = time.time()
    while yet_to_read > 0:
        limit = min(conf.getint('client', 'max_recv_per_read'), yet_to_read)
        try:
            read_this_time = len(sock.recv(limit))
        except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
            log.info(e)
            return
        if read_this_time == 0:
            return
        yet_to_read -= read_this_time
    end_time = time.time()
    return end_time - start_time


def measure_rtt_to_server(sock, conf):
    ''' Make multiple end-to-end RTT measurements. If something goes wrong and
    not all of them can be made, return None. Otherwise return a list of the
    RTTs (in seconds). '''
    rtts = []
    for _ in range(0, conf.getint('client', 'num_rtts')):
        start_time = time.time()
        if not tell_server_amount(sock, 1):
            log.info('Unable to ping server on', sock.fileno())
            return
        try:
            amount_read = len(sock.recv(1))
        except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
            log.info(e)
            return
        end_time = time.time()
        if amount_read == 0:
            log.info('No pong from server on', sock.fileno())
            return
        rtts.append(end_time - start_time)
    return rtts


def measure_relay(args, conf, helpers, cb, rl, relay):
    ''' Runs in a worker thread. Measures the given relay. If all measurements
    are successful, returns a ResultSuccess that should get handed off to the
    ResultDump. If the measurement was not a success, returns a ResultError
    type. If the measurement was not successful, but we known it isn't the
    target relay's fault, return None. Only Result* types get recorded in the
    ResultDump.

    In more detail:
    1. build a two hops circuit from the relay we are measuring to the helper
       relay
    2. listen for stream creations, connect to the server, and (in the
       background during connect) attach the resulting steam to the circuit
       we built
    3. measure the end-to-end RTT many times
    4. measure throughput on the built circuit, repeat the following until we
       have reached <num_downloads>
       4.1. tell the files server the desired amount of bytes to get
       4.2. get the bytes and the time it took
       4.3. calculate the expected amount of bytes according to:
        - If it hardly took any time at all, greatly increase the amount of
          bytes to read
        - If it went a little too fast, adjust the amount of bytes to read
          so that they'll probably take the target amount of time to download
        - If it took a reaonsable amount of time to download, then record the
          result and read the same amount of bytes next time
        - If it took too long, adjust the amount of bytes to read so that
          they'll probably take the target amount of time to download
       4.4. write down the results

    '''
    helper = helpers.next(blacklist=[relay.fingerprint])
    if not helper:
        log.warn('Unable to get helper to measure', relay.nickname)
        return None
    circ_id = cb.build_circuit([relay.fingerprint, helper.fingerprint])
    if not circ_id:
        log.debug('Could not build circuit involving', relay.nickname)
        return ResultErrorCircuit(
            relay, [relay.fingerprint, helper.fingerprint], helper.server_host)
    circ_fps = cb.get_circuit_path(circ_id)
    # A function that attaches all streams that gets created on
    # connect() to the given circuit
    listener = stem_utils.attach_stream_to_circuit_listener(
        cb.controller, circ_id, log_fn=log.debug)
    with stream_building_lock:
        # Tell stem about our listener so it can attach the stream to the
        # circuit when we connect()
        stem_utils.add_event_listener(
            cb.controller, listener, EventType.STREAM)
        s = make_socket(conf['client']['tor_socks_host'],
                        conf.getint('client', 'tor_socks_port'))
        # This call blocks until we are connected (or give up). We get attched
        # to the right circuit in the background.
        connected = socket_connect(s, helper.server_host, helper.server_port)
        stem_utils.remove_event_listener(cb.controller, listener,
                                         log_fn=log.info)
    if not connected:
        log.info('Unable to connect to', helper.server_host,
                 helper.server_port)
        cb.close_circuit(circ_id)
        return
    if not authenticate_to_server(s, helper.password, log.info):
        log.info('Unable to authenticate to the server')
        res = ResultErrorAuth(
            relay, circ_fps, helper.server_host)
        close_socket(s)
        cb.close_circuit(circ_id)
        return res
    log.debug('Authed to server successfully')
    # FIRST: measure the end-to-end RTT many times
    rtts = measure_rtt_to_server(s, conf)
    if rtts is None:
        close_socket(s)
        cb.close_circuit(circ_id)
        return
    # SECOND: measure throughput on this circuit. Start with what should be a
    # small amount
    results = []
    expected_amount = conf.getint('client', 'initial_read_request')
    num_downloads = conf.getint('client', 'num_downloads')
    download_times = {
        'toofast': conf.getfloat('client', 'download_toofast'),
        'min': conf.getfloat('client', 'download_min'),
        'target': conf.getfloat('client', 'download_target'),
        'max': conf.getfloat('client', 'download_max'),
    }
    while len(results) < num_downloads:
        # Tell the server to send us the current expected_amount.
        if not tell_server_amount(s, expected_amount):
            close_socket(s)
            cb.close_circuit(circ_id)
            return
        # Then read that many bytes from the server and get the time it took to
        # do so
        result_time = timed_recv_from_server(s, conf, expected_amount)
        if result_time is None:
            close_socket(s)
            cb.close_circuit(circ_id)
            return
        # Adjust amount of bytes to download in the next download
        if result_time < download_times['toofast']:
            # Way too fast, greatly increase the amount we ask for
            expected_amount = int(expected_amount * 10)
        elif result_time < download_times['min']:
            # A little too fast, increase the amount we ask for such that it
            # will probably take the target amount of time to download
            expected_amount = int(
                expected_amount * download_times['target'] / result_time)
        elif result_time < download_times['max']:
            # result_time is between min and max, record the result and don't
            # change the expected_amount
            results.append(
                {'duration': result_time, 'amount': expected_amount})
        else:
            # result_time is too large, decrease the amount we ask for such
            # that it will probably take the target amount of time to download
            expected_amount = int(
                expected_amount * download_times['target'] / result_time)
    cb.close_circuit(circ_id)
    return ResultSuccess(rtts, results, relay, circ_fps, helper.server_host)


def result_putter(result_dump):
    ''' Create a function that takes a single argument -- the measurement
    result -- and return that function so it can be used by someone else '''
    def closure(measurement_result):
        return result_dump.queue.put(measurement_result)
    return closure


def result_putter_error(target):
    ''' Create a function that takes a single argument -- an error from a
    measurement -- and return that function so it can be used by someone else
    '''
    def closure(err):
        log.warn('Unhandled exception caught while measuring {}: {} {}'.format(
            target.nickname, type(err), err))
    return closure


def test_speedtest(args, conf):
    controller = None
    controller, error_msg = stem_utils.init_controller_with_config(conf)
    if not controller:
        fail_hard(error_msg, log=log)
    assert controller
    cb = CB(args, conf, log, controller=controller)
    rl = RelayList(args, conf, log, controller=controller)
    rd = ResultDump(args, conf, log, end_event)
    rp = RelayPrioritizer(args, conf, log, rl, rd)
    helpers, error_msg = HelperRelayList.from_config(
        args, conf, log, controller=controller)
    if not helpers:
        fail_hard(error_msg)
    max_pending_results = conf.getint('client', 'measurement_threads')
    pool = Pool(max_pending_results)
    pending_results = []
    while True:
        for target in rp.best_priority():
            log.debug('Measuring', target.nickname)
            callback = result_putter(rd)
            callback_err = result_putter_error(target)
            async_result = pool.apply_async(
                measure_relay, [args, conf, helpers, cb, rl, target], {},
                callback, callback_err)
            pending_results.append(async_result)
            while len(pending_results) >= max_pending_results:
                time.sleep(5)
                pending_results = [r for r in pending_results if not r.ready()]


def gen_parser(sub):
    d = 'The client side of sbws. This should be run on a well-connected '\
        'machine on the Internet with a healthy amount of spare bandwidth. '\
        'This continuously builds circuits, measures relays, and dumps '\
        'results into a datadir, commonly found in ~/.sbws'
    sub.add_parser('client', formatter_class=ArgumentDefaultsHelpFormatter,
                   description=d)


def main(args, conf, log_):
    global log
    log = log_
    if not is_initted(args.directory):
        fail_hard('Sbws isn\'t initialized. Try sbws init', log=log)

    if conf.getint('client', 'measurement_threads') < 1:
        fail_hard('Number of measurement threads must be larger than 1',
                  log=log)

    if conf['tor']['control_type'] not in ['port', 'socket']:
        fail_hard('Must specify either control port or socket. '
                  'Not "{}"'.format(conf['tor']['control_type'], log=log))
    if conf['tor']['control_type'] == 'port':
        try:
            conf.getint('tor', 'control_location')
        except ValueError as e:
            fail_hard('Couldn\'t read control port from config:', e, log=log)
    os.makedirs(conf['paths']['datadir'], exist_ok=True)

    try:
        test_speedtest(args, conf)
    except KeyboardInterrupt as e:
        raise e
    finally:
        end_event.set()
