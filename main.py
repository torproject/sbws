#!/usr/bin/env python3
from relaylist import RelayList
import time
import socks  # PySocks
from stem.control import EventType
#from circuitbuilder import GapsCircuitBuilder as CB
from circuitbuilder import ExitCircuitBuilder as CB
import util.stem as stem_utils


def send_data(s):
    data = b'asdf' * 1000
    for _ in range(0,5):
        s.send(data)
        time.sleep(0.5)


def make_socket():
    s = socks.socksocket()
    s.set_proxy(socks.PROXY_TYPE_SOCKS5, '127.0.0.1', 9009)
    s.settimeout(3)
    return s


def test_circuitbuilder():
    cb = CB()
    circ = cb.build_circuit(4)
    if not circ:
        return
    listener = stem_utils.attach_stream_to_circuit_listener(
        cb.controller, circ)
    stem_utils.add_event_listener(cb.controller, listener, EventType.STREAM)
    s = make_socket()
    try:
        s.connect(('127.0.0.1', 4444))
    except socks.GeneralProxyError as e:
        print(e)
        return
    finally:
        stem_utils.remove_event_listener(cb.controller, listener)
    send_data(s)
    s.close()


def test_relaylist():
    rl = RelayList()
    for _ in range(0, 5):
        print(len(rl.exits), len(rl.guards), len(rl.hsdirs), len(rl.relays))
        print(len(rl.unmeasured), len(rl.measured))
        time.sleep(1)


def main():
    test_circuitbuilder()
    #test_relaylist()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

# pylama:ignore=E265
