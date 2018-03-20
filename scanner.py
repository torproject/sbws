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

end_event = Event()
stream_building_lock = RLock()
MAX_RECV_PER_READ = 1*1024*1024
MIN_TIME_REQUIRED = 5


def fail_hard(*s):
    if s:
        print(*s)
    exit(1)


def make_socket(socks_host, socks_port):
    s = socks.socksocket()
    s.set_proxy(socks.PROXY_TYPE_SOCKS5, socks_host, socks_port)
    s.settimeout(10)
    return s


def close_socket(s):
    try:
        s.shutdown(socket.SHUT_RDWR)
        s.close()
    except Exception:
        pass


def socket_connect(s, addr, port):
    try:
        s.connect((addr, port))
        print('connected to', addr, port, 'via', s.fileno())
    except socks.GeneralProxyError as e:
        print(e)
        return False
    return True


def test_circuitbuilder():
    cb = CB()
    circ = cb.build_circuit(2)
    if not circ:
        return


def tell_server_amount(sock, expected_amount):
    ''' Returns True on success; else False '''
    assert expected_amount > 0
    amount = '{}\n'.format(expected_amount)
    try:
        sock.send(bytes(amount, 'utf-8'))
    except socket.timeout as e:
        print(e)
        return False
    return True


def timed_recv_from_server(sock, yet_to_read):
    ''' Return the time in seconds it took to read <expected_amount> bytes from
    the server. Return None if error '''
    assert yet_to_read > 0
    start_time = time.time()
    while yet_to_read > 0:
        limit = min(MAX_RECV_PER_READ, yet_to_read)
        try:
            read_this_time = len(sock.recv(limit))
        except socket.timeout as e:
            print(e)
            return
        if read_this_time == 0:
            return
        yet_to_read -= read_this_time
    end_time = time.time()
    return end_time - start_time


def measure_relay(args, cb, rl, relay):
    circ_id = cb.build_circuit([relay.fingerprint, args.helper_relay])
    if not circ_id:
        return
    listener = stem_utils.attach_stream_to_circuit_listener(
        cb.controller, circ_id)
    with stream_building_lock:
        stem_utils.add_event_listener(
            cb.controller, listener, EventType.STREAM)
        s = make_socket(args.socks_host, args.socks_port)
        #connected = socket_connect(s, '169.254.0.15', 4444)
        #connected = socket_connect(s, '144.217.254.208', 4444)
        connected = socket_connect(s, args.server_host, args.server_port)
        stem_utils.remove_event_listener(cb.controller, listener)
    if not connected:
        cb.close_circuit(circ_id)
        return
    result_time = None
    expected_amount = 16*1024
    while result_time is None or result_time < MIN_TIME_REQUIRED:
        if not tell_server_amount(s, expected_amount):
            close_socket(s)
            cb.close_circuit(circ_id)
            return
        result_time = timed_recv_from_server(s, expected_amount)
        if result_time is None:
            close_socket(s)
            cb.close_circuit(circ_id)
            return
        if result_time > 1:
            expected_amount = int(
                expected_amount * MIN_TIME_REQUIRED / result_time * 1.1)
        else:
            expected_amount = int(expected_amount * 10)
    circ = cb.get_circuit_path(circ_id)
    cb.close_circuit(circ_id)
    return Result(relay, circ, args.server_host, result_time, expected_amount)


def result_putter(result_dump):
    def closure(measurement_result):
        return result_dump.queue.put(measurement_result)
    return closure


def result_putter_error(target):
    def closure(err):
        print('Error measuring', target.nickname, ':', err)


def test_speedtest(args):
    cb = CB(args)
    rl = RelayList(args)
    rd = ResultDump(args.result_directory, end_event)
    max_pending_results = args.threads
    pool = Pool(max_pending_results)
    pending_results = []
    #for target in [rl.random_relay() for _ in range(0, 1)]:
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
        #transfer_time = measure_relay(cb, rl, target)
        #if transfer_time is None:
        #    print('Unable to get transfer time for', target.nickname)
        #    continue
        #res = (target.fingerprint, transfer_time)
        #rd.queue.put(res)
    print('Waiting for all results')
    for r in pending_results:
        #print('get', r.get())
        r.wait()
    print('Got all results')


def main(args):
    #test_circuitbuilder()
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
