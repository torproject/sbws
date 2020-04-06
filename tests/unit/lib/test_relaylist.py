"""relaylist.py unit tests."""
from datetime import datetime

# When datetime is imported as a class (`from datetime import datetime`) it can
# not be mocked because it is a built-in type. It can only be mocked when
# imported as module.
# freezegun is able to mock any datetime object, it also allows comparations.
from freezegun import freeze_time

from sbws.lib.relaylist import Relay, RelayList
from sbws.util.state import State


def test_init_relays(
    args, conf, controller, controller_1h_later, controller_5days_later
):
    """
    Test `init_relays` when creating the RelayList the first time and when a
    new consensus is received.
    Test that the number of consesus timesamps and relays is correct.
    """
    state = State(conf['paths']['state_fpath'])
    # There is no need to mock datetime to update the consensus, since the
    # actual date will be always later.
    # But it's needed to have the correct list of timestamps both for RelayList
    # and Relay.
    with freeze_time("2020-02-29 10:00:00"):
        relay_list = RelayList(args, conf, controller, state=state)
    assert relay_list.recent_consensus_count == 1
    assert relay_list._relays[0].relay_in_recent_consensus_count == 1
    # The actual number of relays in the consensus
    assert len(relay_list._relays) == 6433
    fps = {r.fingerprint for r in relay_list._relays}

    # One hour later there is a new consensus
    relay_list._controller = controller_1h_later
    with freeze_time("2020-02-29 11:00:00"):
        # Call relays update the list of relays.
        relay_list.relays
    assert relay_list.recent_consensus_count == 2
    assert relay_list._relays[0].relay_in_recent_consensus_count == 2
    # Check that the number of relays is now the previous one plus the relays
    # that are in the new consensus that there were not in the previous one.
    fps_1h_later = {r.fingerprint for r in relay_list._relays}
    added_fps = fps_1h_later.difference(fps)
    assert 6505 == 6433 + len(added_fps)

    # Five days later plus 1 second.
    # The first consensus timestamp will get removed.
    relay_list._controller = controller_5days_later
    with freeze_time("2020-03-05 10:00:01"):
        relay_list.relays
    assert relay_list.recent_consensus_count == 2
    assert relay_list._relays[0].relay_in_recent_consensus_count == 2
    fps_5days_later = {r.fingerprint for r in relay_list._relays}
    # The number of added relays will be the number of relays in this
    # consensus that were not in the other 2 conensuses
    added_fps = fps_5days_later.difference(fps_1h_later)
    # The number of removed relays that are in this consensus, plus the added
    # ones that were not in the first consensus (because it has been removed).
    removed_fps = fps.difference(fps_5days_later)
    # The number of relays will be the number of relays in the cosensus plus
    # the added ones minus the removed ones.
    assert 6925 == 6505 + len(added_fps) - len(removed_fps)


def test_increment_recent_measurement_attempt(args, conf, controller):
    """Test that incrementing the measurement attempts does not go on forever

    And instead it only counts the number of attempts in the last days.
    It also tests that the state file is updated correctly.
    """
    state = State(conf['paths']['state_fpath'])
    # For this test it does not matter that the consensus timestamps or relays
    # are not correct.
    relay_list = RelayList(args, conf, controller=controller, state=state)
    # The initial count is 0 and the state does not have that key.
    assert 0 == relay_list.recent_measurement_attempt_count
    assert not state.get("recent_measurement_attempt", None)

    # Pretend that a measurement attempt is made.
    with freeze_time("2020-02-29 10:00:00"):
        relay_list.increment_recent_measurement_attempt()
    assert 1 == relay_list.recent_measurement_attempt_count
    assert [datetime(2020, 2, 29, 10, 0)] == state[
        "recent_measurement_attempt"
    ]

    # And a second measurement attempt is made 4 days later.
    with freeze_time("2020-03-04 10:00:00"):
        relay_list.increment_recent_measurement_attempt()
    assert 2 == relay_list.recent_measurement_attempt_count
    assert 2 == len(state["recent_measurement_attempt"])

    # And a third measurement attempt is made 5 days later.
    with freeze_time("2020-03-05 10:00:00"):
        relay_list.increment_recent_measurement_attempt()
    assert 3 == relay_list.recent_measurement_attempt_count
    assert 3 == len(state["recent_measurement_attempt"])

    # And a fourth measurement attempt is made 6 days later. The first one is
    # now removed and not counted.
    with freeze_time("2020-03-06 10:00:00"):
        relay_list.increment_recent_measurement_attempt()
    assert 3 == relay_list.recent_measurement_attempt_count
    assert 3 == len(state["recent_measurement_attempt"])


def test_increment_relay_recent_measurement_attempt(
    controller, router_status, server_descriptor
):
    """Test that incrementing the measurement attempts does not grow foreever

    And instead it only counts the number of attempts in the last days.
    """
    # For this test it does not matter that the consensus timestamps
    # are not correct.
    now = datetime.utcnow()
    relay = Relay("A" * 40, controller, timestamp=now)
    # The initial count is 0 and the state does not have that key.
    assert 0 == relay.relay_recent_measurement_attempt_count

    # Pretend that a measurement attempt is made.
    with freeze_time("2020-02-29 10:00:00"):
        relay.increment_relay_recent_measurement_attempt()
    assert 1 == relay.relay_recent_measurement_attempt_count

    # And a second measurement attempt is made 4 days later.
    with freeze_time("2020-03-04 10:00:00"):
        relay.increment_relay_recent_measurement_attempt()
    assert 2 == relay.relay_recent_measurement_attempt_count

    # And a third measurement attempt is made 5 days later.
    with freeze_time("2020-03-05 10:00:00"):
        relay.increment_relay_recent_measurement_attempt()
    assert 3 == relay.relay_recent_measurement_attempt_count

    # And a forth measurement attempt is made 6 days later. The first one is
    # now removed and not counted.
    with freeze_time("2020-03-06 10:00:00"):
        relay.increment_relay_recent_measurement_attempt()
    assert 3 == relay.relay_recent_measurement_attempt_count
    # XXX: Write to a Result and load it back


def test_increment_relay_recent_priority_list(
    controller, router_status, server_descriptor
):
    """Test that incrementing the measurement attempts does not grow foreever

    And instead it only counts the number of attempts in the last days.
    """
    # For this test it does not matter that the consensus timestamps
    # are not correct.
    now = datetime.utcnow()
    relay = Relay("A" * 40, controller, timestamp=now)
    # The initial count is 0 and the state does not have that key.
    assert 0 == relay.relay_recent_priority_list_count

    # Pretend that a measurement attempt is made.
    with freeze_time("2020-02-29 10:00:00"):
        relay.increment_relay_recent_priority_list()
    assert 1 == relay.relay_recent_priority_list_count

    # And a second measurement attempt is made 4 days later.
    with freeze_time("2020-03-04 10:00:00"):
        relay.increment_relay_recent_priority_list()
    assert 2 == relay.relay_recent_priority_list_count

    # And a third measurement attempt is made 5 days later.
    with freeze_time("2020-03-05 10:00:00"):
        relay.increment_relay_recent_priority_list()
    assert 3 == relay.relay_recent_priority_list_count

    # And a forth measurement attempt is made 6 days later. The first one is
    # now removed and not counted.
    with freeze_time("2020-03-06 10:00:00"):
        relay.increment_relay_recent_priority_list()
    assert 3 == relay.relay_recent_priority_list_count
