"""Integration tests for destination.py"""
import sbws.util.requests as requests_utils
from sbws.lib.destination import (DestinationList, Destination,
                                  connect_to_destination_over_circuit)


def test_destination_list_no_usability_test_success(
        conf, persistent_launch_tor, cb, rl
        ):
    # In a future refactor, if DestionationList is not initialized with the
    # controller, this test should be an unit test.
    destination_list, error_msg = DestinationList.from_config(
        conf, cb, rl, persistent_launch_tor
        )
    # Initially all destinations should be "usable".
    assert destination_list._all_dests == destination_list._usable_dests
    # Because this is disabled.
    assert destination_list._should_perform_usability_test() is False
    # Because there's only 1 destination in conftest, random should return
    # the same one.
    assert destination_list.next() == \
        destination_list._all_dests[0]


def test_connect_to_destination_over_circuit_success(persistent_launch_tor,
                                                     dests, cb, rl):
    destination = dests.next()
    session = requests_utils.make_session(persistent_launch_tor, 10)
    # Choose a relay that is not an exit
    relay = [r for r in rl.relays
             if r.nickname == 'relay1mbyteMAB'][0]
    # Choose an exit, for this test it does not matter the bandwidth
    helper = rl.exits_not_bad_allowing_port(destination.port)[0]
    circuit_path = [relay.fingerprint, helper.fingerprint]
    # build a circuit
    circuit_id = cb.build_circuit(circuit_path)
    # Perform "usability test"
    is_usable, response = connect_to_destination_over_circuit(
        destination, circuit_id, session, persistent_launch_tor, 1024)
    assert is_usable is True
    assert 'content_length' in response


def test_connect_to_destination_over_circuit_fail(persistent_launch_tor,
                                                  dests, cb, rl):
    bad_destination = Destination('https://example.example', 1024, False)
    # dests._all_dests.append(bad_destination)
    # dests._usable_dests.append(bad_destination)
    session = requests_utils.make_session(persistent_launch_tor, 10)
    # Choose a relay that is not an exit
    relay = [r for r in rl.relays
             if r.nickname == 'relay1mbyteMAB'][0]
    # Choose an exit, for this test it does not matter the bandwidth
    helper = rl.exits_not_bad_allowing_port(bad_destination.port)[0]
    circuit_path = [relay.fingerprint, helper.fingerprint]
    # Build a circuit.
    circuit_id = cb.build_circuit(circuit_path)
    # Perform "usability test"
    is_usable, response = connect_to_destination_over_circuit(
        bad_destination, circuit_id, session, persistent_launch_tor, 1024)
    assert is_usable is False
