#!/usr/bin/env python3
#from circuitbuilder import GapsCircuitBuilder as CB
from circuitbuilder import ExitCircuitBuilder as CB
from relaylist import RelayList
import time


def test_circuitbuilder():
    cb = CB()
    circ = cb.build_circuit(2)
    #circ = cb.build_circuit(['ButtersStotch', None, 'marsbarsarethars'])
    #time.sleep(1)
    #circ = cb.build_circuit(2)
    #circ = cb.build_circuit(['ButtersStotch', None, 'marsbarsarethars'])
    #time.sleep(1)
    #circ = cb.build_circuit(2)
    #circ = cb.build_circuit(['ButtersStotch', None, 'marsbarsarethars'])
    #time.sleep(1)
    #circ = cb.build_circuit(2)
    #circ = cb.build_circuit(['ButtersStotch', None, 'marsbarsarethars'])
    #time.sleep(1)
    time.sleep(3)


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
