"""Integration tests for circutibuilder.py"""
import random


def test_build_circuit(cb, rl):
    # Path is empty
    path = []
    circuit_id, _ = cb.build_circuit(path)
    assert not circuit_id
    # Valid path, not valid exit
    exits = rl.exits_not_bad_allowing_port(port=443)
    # See https://gitlab.torproject.org/tpo/core/chutney/-/issues/40013:
    # Work around to get supposed non-exits because chutney is putting Exit
    # flag to all relays
    non_exits = list(set(rl.exits).difference(set(exits)))
    entry = random.choice(non_exits)
    # Because in chutney all relays are exits, we can't test using a non-exit
    # as 2nd hop.
    # Valid path and relays
    exit_relay = random.choice(exits)
    path = [entry.fingerprint, exit_relay.fingerprint]
    circuit_id, _ = cb.build_circuit(path)
    assert circuit_id
