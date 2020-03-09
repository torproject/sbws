"""relaylist.py unit tests."""
from datetime import datetime, timedelta

# When datetime is imported as a class (`from datetime import datetime`) it can
# not be mocked because it is a built-in type. It can only be mocked when
# imported as module.
# freezegun is able to mock any datetime object, it also allows comparations.
from freezegun import freeze_time

from sbws.lib.relaylist import RelayList, remove_old_consensus_timestamps


def test_remove_old_consensus_timestamps():
    days_ago = datetime(2020, 3, 1)
    timestamps = [days_ago] + [
        days_ago + timedelta(days=x) for x in range(1, 5)
    ]
    with freeze_time(days_ago + timedelta(days=5, seconds=1)):
        new_timestamps = remove_old_consensus_timestamps(
            timestamps, 5 * 24 * 60 * 60
        )
    assert len(new_timestamps) == len(timestamps) - 1
    assert days_ago not in new_timestamps


def test_init_relays(
    args, conf, controller, controller_1h_later, controller_5days_later
):
    """
    Test `init_relays` when creating the RelayList the first time and when a
    new consensus is received.
    Test that the number of consesus timesamps and relays is correct.
    """
    # There is no need to mock datetime to update the consensus, since the
    # actual date will be always later.
    # But it's needed to have the correct list of timestamps both for RelayList
    # and Relay.
    with freeze_time("2020-02-29 10:00:00"):
        relay_list = RelayList(args, conf, controller=controller)
    assert len(relay_list._consensus_timestamps) == 1
    assert len(relay_list._relays[0]._consensus_timestamps) == 1
    # The actual number of relays in the consensus
    assert len(relay_list._relays) == 6433
    fps = {r.fingerprint for r in relay_list._relays}

    # One hour later there is a new consensus
    relay_list._controller = controller_1h_later
    with freeze_time("2020-02-29 11:00:00"):
        # Call relays update the list of relays.
        relay_list.relays
    assert len(relay_list._consensus_timestamps) == 2
    assert len(relay_list._relays[0]._consensus_timestamps) == 2
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
    assert len(relay_list._consensus_timestamps) == 2
    assert len(relay_list._relays[0]._consensus_timestamps) == 2
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
