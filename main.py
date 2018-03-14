#!/usr/bin/env python3
from circuitbuilder import GapsCircuitBuilder as CB
from relaylist import RelayList
from resultdump import ResultDump
import util.stem as stem_utils
import random
import time
import socks  # PySocks
import socket
from stem.control import EventType
from threading import Event
from multiprocessing.dummy import Pool

end_event = Event()


def make_socket():
    s = socks.socksocket()
    s.set_proxy(socks.PROXY_TYPE_SOCKS5, '127.0.0.1', 9050)
    s.settimeout(10)
    return s


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


def measure_relay(cb, rl, relay):
    circ = cb.build_circuit([None, relay.fingerprint, 'KISTrulez'])
    if not circ:
        return
    listener = stem_utils.attach_stream_to_circuit_listener(cb.controller, circ)
    stem_utils.add_event_listener(cb.controller, listener, EventType.STREAM)
    s = make_socket()
    #connected = socket_connect(s, '169.254.0.15', 4444)
    connected = socket_connect(s, '144.217.254.208', 4444)
    stem_utils.remove_event_listener(cb.controller, listener)
    if not connected:
        return
    start_time = time.time()
    total_fetched = 0
    try:
        just_fetched = len(s.recv(4096))
    except socket.timeout as e:
        print(e)
        try: s.close()
        except: pass
        return
    while just_fetched > 0:
        total_fetched += just_fetched
        try:
            just_fetched = len(s.recv(4096))
        except socket.timeout as e:
            print(e)
            try: s.close()
            except: pass
            return
    end_time = time.time()
    s.close()
    cb.close_circuit(circ)
    return end_time - start_time

def result_putter(result_dump, target):
    def closure(transfer_time):
        return result_dump.queue.put((target.nickname, transfer_time))
    return closure

def test_speedtest():
    cb = CB()
    rl = RelayList()
    rd = ResultDump('./dd', end_event)
    max_pending_results = 3
    pool = Pool(max_pending_results)
    pending_results = []
    for target in [rl.random_relay() for _ in range(0, 7)]:
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
