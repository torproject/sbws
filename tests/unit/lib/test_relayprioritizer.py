"""relayprioritizer.py unit tests."""
from freezegun import freeze_time


def test_increment_recent_priority_list(relay_prioritizer):
    """Test that incrementing the priority lists do not go on forever.

    And instead it only counts the number of priority lists in the last days.
    """

    state = relay_prioritizer._state
    assert 0 == relay_prioritizer.recent_priority_list_count
    assert not state.get("recent_priority_list", None)

    # Pretend that a priority list is made.
    with freeze_time("2020-02-29 10:00:00"):
        relay_prioritizer.increment_recent_priority_list()
    assert 1 == relay_prioritizer.recent_priority_list_count
    assert 1 == len(state["recent_priority_list"])

    # And a second priority list is made 4 days later.
    with freeze_time("2020-03-04 10:00:00"):
        relay_prioritizer.increment_recent_priority_list()
    assert 2 == relay_prioritizer.recent_priority_list_count
    assert 2 == len(state["recent_priority_list"])

    # And a third priority list is made 5 days later.
    with freeze_time("2020-03-05 10:00:00"):
        relay_prioritizer.increment_recent_priority_list()
    assert 3 == relay_prioritizer.recent_priority_list_count
    assert 3 == len(state["recent_priority_list"])

    # And a fourth priority list is made 6 days later. The first one is
    # now removed and not counted.
    with freeze_time("2020-03-06 10:00:00"):
        relay_prioritizer.increment_recent_priority_list()
    assert 3 == relay_prioritizer.recent_priority_list_count
    assert 3 == len(state["recent_priority_list"])


def test_increment_priority_relay(relay_prioritizer):
    """Test that incrementing the number of relays in the priority lists
    do not go on forever.

    And instead it only counts number of relays in priority lists in the last
    days.
    """

    state = relay_prioritizer._state
    assert 0 == relay_prioritizer.recent_priority_relay_count
    assert not state.get("recent_priority_relay", None)

    # Pretend that a priority list is made.
    with freeze_time("2020-02-29 10:00:00"):
        relay_prioritizer.increment_recent_priority_relay(2)
    assert 2 == relay_prioritizer.recent_priority_relay_count
    assert 2 == state.count("recent_priority_relay")

    # And a second priority list is made 4 days later.
    with freeze_time("2020-03-04 10:00:00"):
        relay_prioritizer.increment_recent_priority_relay(2)
    assert 4 == relay_prioritizer.recent_priority_relay_count
    assert 4 == state.count("recent_priority_relay")

    # And a third priority list is made 5 days later.
    with freeze_time("2020-03-05 10:00:00"):
        relay_prioritizer.increment_recent_priority_relay(2)
    assert 6 == relay_prioritizer.recent_priority_relay_count
    assert 6 == state.count("recent_priority_relay")

    # And a fourth priority list is made 6 days later. The first one is
    # now removed and the relays are not counted.
    with freeze_time("2020-03-06 10:00:00"):
        relay_prioritizer.increment_recent_priority_relay(2)
    assert 6 == relay_prioritizer.recent_priority_relay_count
    assert 6 == state.count("recent_priority_relay")
