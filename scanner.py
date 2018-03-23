#!/usr/bin/env python3
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
import time
import socks  # PySocks
import socket
import random
from stem.control import EventType
from threading import Event
from threading import RLock
from multiprocessing.dummy import Pool
import util.stem as stem_utils
from lib.circuitbuilder import GapsCircuitBuilder as CB
from lib.resultdump import ResultDump
from lib.resultdump import Result
from lib.relaylist import RelayList
from lib.pastlylogger import PastlyLogger

end_event = Event()
stream_building_lock = RLock()
log = PastlyLogger(debug='/dev/stdout', overwrite=['debug'], log_threads=True)

# maximum we want to read per read() call
MAX_RECV_PER_READ = 1*1024*1024
DOWNLOAD_TIMES = {'toofast': 1, 'min': 5, 'target': 6, 'max': 10}
DESIRED_RESULTS = 5


def fail_hard(*s):
    ''' Optionally log something to stdout ... and then exit as fast as
    possible '''
    if s:
        log.error(*s)
    exit(1)


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
    except (socks.GeneralProxyError, socks.ProxyConnectionError) as e:
        log.warn(e)
        return False
    return True


def tell_server_amount(sock, expected_amount):
    ''' Returns True on success; else False '''
    assert expected_amount > 0
    # Expectd_amount should come in as an int, but we send it to the server as
    # a string (ignore the difference between bytes and str in python. You know
    # what I mean).
    amount = '{}\n'.format(expected_amount)
    try:
        sock.send(bytes(amount, 'utf-8'))
    except socket.timeout as e:
        log.info(e)
        return False
    return True


def timed_recv_from_server(sock, yet_to_read):
    ''' Return the time in seconds it took to read <yet_to_read> bytes from
    the server. Return None if error '''
    assert yet_to_read > 0
    start_time = time.time()
    while yet_to_read > 0:
        limit = min(MAX_RECV_PER_READ, yet_to_read)
        try:
            read_this_time = len(sock.recv(limit))
        except socket.timeout as e:
            log.info(e)
            return
        if read_this_time == 0:
            return
        yet_to_read -= read_this_time
    end_time = time.time()
    return end_time - start_time


def measure_rtt_to_server(sock):
    ''' Make multiple end-to-end RTT measurements. If something goes wrong and
    not all of them can be made, return None. Otherwise return a list of the
    RTTs (in seconds). '''
    rtts = []
    for _ in range(0, 10):
        start_time = time.time()
        if not tell_server_amount(sock, 1):
            log.info('Unable to ping server on', sock.fileno())
            return
        amount_read = len(sock.recv(1))
        end_time = time.time()
        if amount_read == 0:
            log.info('No pong from server on', sock.fileno())
            return
        rtts.append(end_time - start_time)
    return rtts


def measure_relay(args, cb, rl, relay):
    ''' Runs in a worker thread. Measures the given relay. If all measurements
    are successful, returns a Result that should get handed off to the
    ResultDump. Otherwise returns None '''
    circ_id = cb.build_circuit([relay.fingerprint, args.helper_relay])
    if not circ_id:
        return
    # A function that attaches all streams that gets created on
    # connect() to the given circuit
    listener = stem_utils.attach_stream_to_circuit_listener(
        cb.controller, circ_id, log_fn=log.debug)
    with stream_building_lock:
        # Tell stem about our listener so it can attach the stream to the
        # circuit when we connect()
        stem_utils.add_event_listener(
            cb.controller, listener, EventType.STREAM)
        s = make_socket(args.socks_host, args.socks_port)
        # This call blocks until we are connected (or give up). We get attched
        # to the right circuit in the background.
        connected = socket_connect(s, args.server_host, args.server_port)
        stem_utils.remove_event_listener(cb.controller, listener,
                                         log_fn=log.info)
    if not connected:
        log.info('Unable to connect to', args.server_host, args.server_port)
        cb.close_circuit(circ_id)
        return
    # FIRST: measure the end-to-end RTT many times
    rtts = measure_rtt_to_server(s)
    if rtts is None:
        close_socket(s)
        cb.close_circuit(circ_id)
        return
    # SECOND: measure throughput on this sircuit. Start with what should be a
    # small amount
    results = []
    expected_amount = 16*1024
    while len(results) < DESIRED_RESULTS:
        # Tell the server to send us the current expected_amount.
        if not tell_server_amount(s, expected_amount):
            close_socket(s)
            cb.close_circuit(circ_id)
            return
        # Then read that many bytes from the server and get the time it took to
        # do so
        result_time = timed_recv_from_server(s, expected_amount)
        if result_time is None:
            close_socket(s)
            cb.close_circuit(circ_id)
            return
        if result_time < DOWNLOAD_TIMES['toofast']:
            expected_amount = int(expected_amount * 10)
        elif result_time < DOWNLOAD_TIMES['min']:
            expected_amount = int(
                expected_amount * DOWNLOAD_TIMES['target'] / result_time)
        elif result_time < DOWNLOAD_TIMES['target']:
            results.append(
                {'duration': result_time, 'amount': expected_amount})
        elif result_time < DOWNLOAD_TIMES['max']:
            results.append(
                {'duration': result_time, 'amount': expected_amount})
        else:
            expected_amount = int(
                expected_amount * DOWNLOAD_TIMES['target'] / result_time)
    circ = cb.get_circuit_path(circ_id)
    cb.close_circuit(circ_id)
    return Result(relay, circ, args.server_host, rtts, results)


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


def test_speedtest(args):
    controller = stem_utils.init_controller(
        port=args.control[1] if args.control[0] == 'port' else None,
        path=args.control[1] if args.control[0] == 'socket' else None,
        log_fn=log.debug)
    cb = CB(args, log, controller=controller)
    rl = RelayList(args, log, controller=controller)
    rd = ResultDump(log, args.result_directory, end_event)
    max_pending_results = args.threads
    pool = Pool(max_pending_results)
    pending_results = []
    relays = rl.relays
    random.shuffle(relays)
    for target in relays:
        callback = result_putter(rd)
        callback_err = result_putter_error(target)
        async_result = pool.apply_async(
            measure_relay, [args, cb, rl, target], {},
            callback, callback_err)
        pending_results.append(async_result)
        while len(pending_results) >= max_pending_results:
            time.sleep(5)
            pending_results = [r for r in pending_results if not r.ready()]
    log.notice('Waiting for all results')
    for r in pending_results:
        r.wait()
    log.notice('Got all results')


def main(args):
    test_speedtest(args)


if __name__ == '__main__':
    parser = ArgumentParser(
            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--control', nargs=2, metavar=('TYPE', 'LOCATION'),
                        default=['port', '9051'],
                        help='How to control Tor. Examples: "port 9051" or '
                        '"socket /var/lib/tor/control"')
    parser.add_argument('--socks-host', default='127.0.0.1', type=str,
                        help='Host for a local Tor SocksPort')
    parser.add_argument('--socks-port', default=9050, type=int,
                        help='Port for a local Tor SocksPort')
    parser.add_argument('--server-host', default='127.0.0.1', type=str,
                        help='Host for a measurement server')
    parser.add_argument('--server-port', default=4444, type=int,
                        help='Port for a measurement server')
    parser.add_argument('--result-directory', default='dd', type=str,
                        help='Where to store raw result output')
    parser.add_argument('--threads', default=1, type=int,
                        help='Number of measurements to make in parallel')
    parser.add_argument('--helper-relay', type=str, required=True,
                        help='Relay to which to build circuits and is running '
                        'the server.py')

    args = parser.parse_args()
    if args.threads < 1:
        fail_hard('--threads must be larger than 1')
    if args.control[0] not in ['port', 'socket']:
        fail_hard('Must specify either control port or socket. '
                  'Not "{}"'.format(args.control[0]))
    if args.control[0] == 'port':

        args.control[1] = int(args.control[1])
    try:
        main(args)
    except KeyboardInterrupt as e:
        raise e
    finally:
        end_event.set()

# pylama:ignore=E265
