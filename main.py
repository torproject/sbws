#!/usr/bin/env python3
from circuitbuilder import GapsCircuitBuilder
import time


def main():
    cb = GapsCircuitBuilder()
    circ = cb.build_circuit(['ButtersStotch', None, 'marsbarsarethars'])
    time.sleep(1)
    cb.close_circuit(circ)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
