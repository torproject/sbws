#!/usr/bin/env python3
from circuitbuilder import GapsCircuitBuilder as CB
from relaylist import RelayList
from resultdump import ResultDump
import util.stem as stem_utils
import random
import time
import socks  # PySocks
import socket
import random
from stem.control import EventType
from threading import Event
from threading import RLock
from multiprocessing.dummy import Pool

end_event = Event()
stream_building_lock = RLock()
MAX_RECV_PER_READ = 1*1024*1024


def make_socket():
    s = socks.socksocket()
    s.set_proxy(socks.PROXY_TYPE_SOCKS5, '127.0.0.1', 9009)
    s.settimeout(3)
    return s


def close_socket(s):
    s.shutdown(socket.SHUT_RDWR)
    s.close()
    #try:
    #    s.shutdown(socket.SHUT_RDWR)
    #    s.close()
    #except Exception:
    #    pass


def socket_connect(s, addr, port):
    try:
        s.connect((addr, port))
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


def measure_relay(cb, rl, relay):
    circ = cb.build_circuit([relay.fingerprint, None])
    if not circ:
        return
    listener = stem_utils.attach_stream_to_circuit_listener(cb.controller, circ)
    with stream_building_lock:
        stem_utils.add_event_listener(cb.controller, listener, EventType.STREAM)
        s = make_socket()
        #connected = socket_connect(s, '169.254.0.15', 4444)
        #connected = socket_connect(s, '144.217.254.208', 4444)
        connected = socket_connect(s, '127.0.0.1', 4444)
        stem_utils.remove_event_listener(cb.controller, listener)
    if not connected:
        return
    expected_amount = random.randint(10*1024*1024, 100*1024*1024)
    #expected_amount = random.randint(1*1024*1024, 2*1024*1024)
    amount = '{}\n'.format(expected_amount)
    try:
        s.send(bytes(amount, 'utf-8'))
    except socket.timeout as e:
        print(e)
        close_socket(s)
        return
    start_time = time.time()
    yet_to_read = expected_amount
    while yet_to_read > 0:
        limit = min(MAX_RECV_PER_READ, yet_to_read)
        read_this_time = len(s.recv(limit))
        if read_this_time == 0:
            close_socket(s)
            return
        yet_to_read -= read_this_time
    end_time = time.time()
    close_socket(s)
    cb.close_circuit(circ)
    return make_result(end_time - start_time, expected_amount)

def result_putter(result_dump, target):
    def closure(measurement_result):
        return result_dump.queue.put((target.nickname, measurement_result))
    return closure

def test_speedtest():
    cb = CB()
    rl = RelayList()
    rd = ResultDump('./dd', end_event)
    max_pending_results = 16
    pool = Pool(max_pending_results)
    pending_results = []
    for target in [rl.random_relay() for _ in range(0, 1)]:
    #for target in rl.relays:
        async_result = pool.apply_async(
                measure_relay, [cb, rl, target], {}, result_putter(rd, target))
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
    end_event.set()


def main():
    #test_circuitbuilder()
    test_speedtest()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        end_event.set()
        pass

# pylama:ignore=E265
