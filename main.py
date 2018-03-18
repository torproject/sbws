#!/usr/bin/env python3
import time
import socks  # PySocks
import socket
from stem.control import EventType
from threading import Event
from threading import RLock
from multiprocessing.dummy import Pool
import util.stem as stem_utils
from circuitbuilder import GapsCircuitBuilder as CB
from relaylist import RelayList
from resultdump import ResultDump

end_event = Event()
stream_building_lock = RLock()
MAX_RECV_PER_READ = 1*1024*1024
MIN_TIME_REQUIRED = 5


def make_socket():
    s = socks.socksocket()
    s.set_proxy(socks.PROXY_TYPE_SOCKS5, '127.0.0.1', 9009)
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


def make_result(ttime, tamount):
    return {'time': ttime, 'amount': tamount}


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


def measure_relay(cb, rl, relay):
    circ = cb.build_circuit([relay.fingerprint, None])
    if not circ:
        return
    listener = stem_utils.attach_stream_to_circuit_listener(
        cb.controller, circ)
    with stream_building_lock:
        stem_utils.add_event_listener(
            cb.controller, listener, EventType.STREAM)
        s = make_socket()
        #connected = socket_connect(s, '169.254.0.15', 4444)
        #connected = socket_connect(s, '144.217.254.208', 4444)
        connected = socket_connect(s, '127.0.0.1', 4444)
        stem_utils.remove_event_listener(cb.controller, listener)
    if not connected:
        cb.close_circuit(circ)
        return
    result_time = None
    expected_amount = 16*1024
    while result_time is None or result_time < MIN_TIME_REQUIRED:
        if not tell_server_amount(s, expected_amount):
            close_socket(s)
            cb.close_circuit(circ)
            return
        result_time = timed_recv_from_server(s, expected_amount)
        if result_time is None:
            close_socket(s)
            cb.close_circuit(circ)
            return
        if result_time > 1:
            expected_amount = int(
                expected_amount * MIN_TIME_REQUIRED / result_time * 1.1)
        else:
            expected_amount = int(expected_amount * 10)
    cb.close_circuit(circ)
    return make_result(result_time, expected_amount)

def result_putter(result_dump, target):
    def closure(measurement_result):
        return result_dump.queue.put((target.nickname, measurement_result))
    return closure


def test_speedtest():
    cb = CB()
    rl = RelayList()
    rd = ResultDump('./dd', end_event)
    max_pending_results = 2
    pool = Pool(max_pending_results)
    pending_results = []
    #for target in [rl.random_relay() for _ in range(0, 1)]:
    for target in rl.relays:
        callback = result_putter(rd, target)
        async_result = pool.apply_async(
                measure_relay, [cb, rl, target], {}, callback, callback)
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


def main():
    #test_circuitbuilder()
    test_speedtest()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        raise e
    finally:
        end_event.set()

# pylama:ignore=E265
