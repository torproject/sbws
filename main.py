#!/usr/bin/env python3
from circuitbuilder import GapsCircuitBuilder as CB
from relaylist import RelayList
import util.stem as stem_utils
import random
import time
import socks  # PySocks
from stem.control import EventType


def make_socket():
    s = socks.socksocket()
    s.set_proxy(socks.PROXY_TYPE_SOCKS5, '127.0.0.1', 9009)
    s.settimeout(3)
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
    circ = cb.build_circuit([None, relay.fingerprint, None])
    if not circ:
        return
    listener = stem_utils.attach_stream_to_circuit_listener(cb.controller, circ)
    stem_utils.add_event_listener(cb.controller, listener, EventType.STREAM)
    s = make_socket()
    connected = socket_connect(s, '127.0.0.1', 4444)
    stem_utils.remove_event_listener(cb.controller, listener)
    if not connected:
        return
    start_time = time.time()
    total_fetched = 0
    just_fetched = len(s.recv(4096000))
    while just_fetched > 0:
        total_fetched += just_fetched
        just_fetched = len(s.recv(4096000))
    end_time = time.time()
    s.close()
    cb.close_circuit(circ)
    return end_time - start_time

def test_speedtest():
    cb = CB()
    rl = RelayList()
    results = []
    for target in rl.relays:
        transfer_time = measure_relay(cb, rl, target)
        if transfer_time is None:
            print('Unable to get transfer time for', target.nickname)
            continue
        results.append((target, transfer_time))
    for res in results:
        print(res[0].nickname, res[1])


def main():
    #test_circuitbuilder()
    test_speedtest()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

# pylama:ignore=E265
