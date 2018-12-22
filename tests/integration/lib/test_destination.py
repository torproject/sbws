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
    assert not destination.failed
    assert destination.consecutive_failures == 0
    assert destination.is_functional


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

    # because it is the first time it fails, failures aren't count
    assert bad_destination.failed
    assert bad_destination.consecutive_failures == 0
    assert bad_destination.is_functional

    # fail twice in a row
    is_usable, response = connect_to_destination_over_circuit(
        bad_destination, circuit_id, session, persistent_launch_tor, 1024)
    assert bad_destination.failed
    assert bad_destination.consecutive_failures == 1
    assert bad_destination.is_functional


def test_functional_destinations(conf, cb, rl, persistent_launch_tor):
    good_destination = Destination('https://127.0.0.1:28888', 1024, False)
    # Mock that it failed before and just now, but it's still considered
    # functional.
    good_destination.consecutive_failures = 3
    good_destination.failed = True
    bad_destination = Destination('https://example.example', 1024, False)
    # Mock that it didn't fail now, but it already failed 11 consecutive
    # times.
    bad_destination.consecutive_failures = 11
    bad_destination.failed = False
    # None of the arguments are used, move to unit tests when this get
    # refactored
    destination_list = DestinationList(
        conf, [good_destination, bad_destination], cb, rl,
        persistent_launch_tor)
    expected_functional_destinations = [good_destination]
    functional_destinations = destination_list.functional_destinations
    assert expected_functional_destinations == functional_destinations
