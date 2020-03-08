"""relaylist.py unit tests."""
from datetime import datetime, timedelta

# When datetime is imported as a class (`from datetime import datetime`) it can
# not be mocked because it is a built-in type. It can only be mocked when
# imported as module.
# freezegun is able to mock any datetime object, it also allows comparations.
from freezegun import freeze_time

from sbws.lib.relaylist import remove_old_consensus_timestamps


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
