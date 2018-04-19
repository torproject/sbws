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
from ..util.sockio import (make_socket, close_socket, socket_connect)
from sbws.globals import (fail_hard, is_initted, time_now)
from sbws.globals import (MIN_REQ_BYTES, MAX_REQ_BYTES)
import sbws.util.stem as stem_utils
from stem.control import EventType
from argparse import ArgumentDefaultsHelpFormatter
from multiprocessing.dummy import Pool
from threading import Event
from threading import RLock
import socket
import time
import os
import logging

end_event = Event()
stream_building_lock = RLock()
log = logging.getLogger(__name__)


def tell_server_amount(sock, expected_amount):
    ''' Returns True on success; else False '''
    assert expected_amount >= MIN_REQ_BYTES
    assert expected_amount <= MAX_REQ_BYTES
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
    start_time = time_now()
    while yet_to_read > 0:
        limit = min(conf.getint('scanner', 'max_recv_per_read'), yet_to_read)
        try:
            read_this_time = len(sock.recv(limit))
        except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
            log.info(e)
            return
        if read_this_time == 0:
            return
        yet_to_read -= read_this_time
    end_time = time_now()
    return end_time - start_time


def measure_rtt_to_server(sock, conf):
    ''' Make multiple end-to-end RTT measurements. If something goes wrong and
    not all of them can be made, return None. Otherwise return a list of the
    RTTs (in seconds). '''
    rtts = []
    for _ in range(0, conf.getint('scanner', 'num_rtts')):
        start_time = time_now()
        if not tell_server_amount(sock, MIN_REQ_BYTES):
            log.info('Unable to ping server on %d', sock.fileno())
            return
        try:
            amount_read = len(sock.recv(1))
        except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
            log.info(e)
            return
        end_time = time_now()
        if amount_read == 0:
            log.info('No pong from server on %d', sock.fileno())
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
    our_nick = conf['scanner']['nickname']
    helper = helpers.next(blacklist=[relay.fingerprint])
    if not helper:
        log.warning('Unable to get helper to measure %s', relay.nickname)
        return None
    circ_id = cb.build_circuit([relay.fingerprint, helper.fingerprint])
    if not circ_id:
        log.debug('Could not build circuit involving %s', relay.nickname)
        return ResultErrorCircuit(
            relay, [relay.fingerprint, helper.fingerprint], helper.server_host,
            our_nick)
    circ_fps = cb.get_circuit_path(circ_id)
    # A function that attaches all streams that gets created on
    # connect() to the given circuit
    listener = stem_utils.attach_stream_to_circuit_listener(
        cb.controller, circ_id)
    with stream_building_lock:
        # Tell stem about our listener so it can attach the stream to the
        # circuit when we connect()
        stem_utils.add_event_listener(
            cb.controller, listener, EventType.STREAM)
        s = make_socket(conf['tor']['socks_host'],
                        conf.getint('tor', 'socks_port'))
        # This call blocks until we are connected (or give up). We get attched
        # to the right circuit in the background.
        connected = socket_connect(s, helper.server_host, helper.server_port)
        stem_utils.remove_event_listener(cb.controller, listener)
    if not connected:
        log.info('Unable to connect to %s:%d', helper.server_host,
                 helper.server_port)
        cb.close_circuit(circ_id)
        return
    if not authenticate_to_server(s, helper.password):
        log.info('Unable to authenticate to the server')
        res = ResultErrorAuth(
            relay, circ_fps, helper.server_host, our_nick)
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
    expected_amount = conf.getint('scanner', 'initial_read_request')
    num_downloads = conf.getint('scanner', 'num_downloads')
    download_times = {
        'toofast': conf.getfloat('scanner', 'download_toofast'),
        'min': conf.getfloat('scanner', 'download_min'),
        'target': conf.getfloat('scanner', 'download_target'),
        'max': conf.getfloat('scanner', 'download_max'),
    }
    while len(results) < num_downloads:
        if expected_amount == MAX_REQ_BYTES:
            log.warning('We are requesting the maximum number of bytes we are '
                        'allowed to ask for from a server in order to measure '
                        '%s via helper %s and we don\'t expect this to happen '
                        'very often', relay.nickname, helper.fingerprint[0:8])
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
        # Determine if we should keep the result we got based on how long it
        # took the download. Then keep it if we should.
        if _should_keep_result(
                expected_amount == MAX_REQ_BYTES, result_time, download_times):
            results.append({
                'duration': result_time, 'amount': expected_amount
            })
        # Recalculate the amount we next will ask for the server to send us
        expected_amount = _next_expected_amount(
            expected_amount, result_time, download_times)
    cb.close_circuit(circ_id)
    return ResultSuccess(rtts, results, relay, circ_fps, helper.server_host,
                         our_nick)


def dispatch_worker_thread(*a, **kw):
    try:
        return measure_relay(*a, **kw)
    except Exception as err:
        log.exception('Unhandled exception in worker thread')
        raise err


def _should_keep_result(did_request_maximum, result_time, download_times):
    # In the normal case, we didn't ask for the maximum allowed amount. So we
    # should only allow ourselves to keep results that are between the min and
    # max allowed time
    if not did_request_maximum and \
            result_time >= download_times['min'] and \
            result_time < download_times['max']:
        return True
    # If we did request the maximum amount, we should keep the result as long
    # as it took less than the maximum amount of time
    if did_request_maximum and \
            result_time < download_times['max']:
        return True
    # In all other cases, return false
    log.debug('Not keeping result time %f.%s', result_time,
              '' if not did_request_maximum else ' We requested the maximum '
              'amount allowed.')
    return False


def _next_expected_amount(expected_amount, result_time, download_times):
    if result_time < download_times['toofast']:
        # Way too fast, greatly increase the amount we ask for
        expected_amount = int(expected_amount * 5)
    elif result_time < download_times['min'] or \
            result_time >= download_times['max']:
        # As long as the result is between min/max, keep the expected amount
        # the same. Otherwise, adjust so we are aiming for the target amount.
        expected_amount = int(
            expected_amount * download_times['target'] / result_time)
    # Make sure we don't request too much or too little
    expected_amount = max(MIN_REQ_BYTES, expected_amount)
    expected_amount = min(MAX_REQ_BYTES, expected_amount)
    return expected_amount


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
        log.error('Unhandled exception caught while measuring %s: %s %s',
                  target.nickname, type(err), err)
    return closure


def run_speedtest(args, conf):
    controller = None
    controller, error_msg = stem_utils.init_controller_with_config(conf)
    if not controller:
        fail_hard(error_msg)
    assert controller
    cb = CB(args, conf, controller=controller)
    rl = RelayList(args, conf, controller=controller)
    rd = ResultDump(args, conf, end_event)
    rp = RelayPrioritizer(args, conf, rl, rd)
    helpers, error_msg = HelperRelayList.from_config(
        args, conf, stream_building_lock, controller=controller)
    if not helpers:
        fail_hard(error_msg)
    max_pending_results = conf.getint('scanner', 'measurement_threads')
    pool = Pool(max_pending_results)
    pending_results = []
    while True:
        for target in rp.best_priority():
            log.debug('Measuring %s', target.nickname)
            callback = result_putter(rd)
            callback_err = result_putter_error(target)
            async_result = pool.apply_async(
                dispatch_worker_thread, [args, conf, helpers, cb, rl, target],
                {}, callback, callback_err)
            pending_results.append(async_result)
            while len(pending_results) >= max_pending_results:
                time.sleep(5)
                pending_results = [r for r in pending_results if not r.ready()]


def gen_parser(sub):
    d = 'The scanner side of sbws. This should be run on a well-connected '\
        'machine on the Internet with a healthy amount of spare bandwidth. '\
        'This continuously builds circuits, measures relays, and dumps '\
        'results into a datadir, commonly found in ~/.sbws'
    sub.add_parser('scanner', formatter_class=ArgumentDefaultsHelpFormatter,
                   description=d)


def main(args, conf):
    if not is_initted(args.directory):
        fail_hard('Sbws isn\'t initialized. Try sbws init')

    if conf.getint('scanner', 'measurement_threads') < 1:
        fail_hard('Number of measurement threads must be larger than 1')

    if conf['tor']['control_type'] not in ['port', 'socket']:
        fail_hard('Must specify either control port or socket. '
                  'Not "%s"', conf['tor']['control_type'])
    if conf['tor']['control_type'] == 'port':
        try:
            conf.getint('tor', 'control_location')
        except ValueError as e:
            fail_hard('Couldn\'t read control port from config: %s', e)
    os.makedirs(conf['paths']['datadir'], exist_ok=True)

    try:
        run_speedtest(args, conf)
    except KeyboardInterrupt as e:
        raise e
    finally:
        end_event.set()
