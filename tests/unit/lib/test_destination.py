"""Unit tests for sbws.lib.destination."""
from datetime import datetime, timedelta

from sbws.globals import MAX_SECONDS_RETRY_DESTINATION
from sbws.lib import destination


def test_destination_is_functional():
    eleven_mins_ago = datetime.utcnow() - timedelta(minutes=11)
    six_mins_ago = datetime.utcnow() - timedelta(minutes=6)
    four_mins_ago = datetime.utcnow() - timedelta(minutes=4)
    # Make last time tried a bit bigger than the half of the maximum, so that
    # it's bigger than the delta time to retry, and when delta time to retry
    # is muliplied by a factor (2) it reaches the maximum.
    long_ago = datetime.utcnow() - timedelta(
        (MAX_SECONDS_RETRY_DESTINATION / 2) + 2
    )

    d = destination.Destination('unexistenturl', 0, False)
    assert d.is_functional()

    # Fail 3 consecutive times
    d.add_failure()
    d.add_failure()
    d.add_failure()
    assert d._are_last_attempts_failures()
    assert not d._is_last_try_old_enough()
    assert not d.is_functional()

    # Then doesn't fail and it's functional again
    d.add_success()
    assert not d._are_last_attempts_failures()
    assert d.is_functional()

    # Fail again 3 times
    d.add_failure()
    d.add_failure()
    # And last failure was 2h ago
    d.add_failure(four_mins_ago)
    assert d._are_last_attempts_failures()
    assert not d._is_last_try_old_enough()
    assert not d.is_functional()

    # But if the last failure was 4h ago, try to use it again
    # And last failure was 4h ago
    d.add_failure(six_mins_ago)
    assert d._is_last_try_old_enough()
    assert d.is_functional()

    # If last failure was 8h ago, try to use it again again
    d.add_failure(eleven_mins_ago)
    assert d._is_last_try_old_enough()
    assert d.is_functional()

    # Whenever it does not fail again, reset the time to try again
    # on 3 consecutive failures
    d.add_success()
    assert not d._are_last_attempts_failures()
    assert d.is_functional()
    # And the delta to try is resetted
    assert not d._is_last_try_old_enough()

    # When the delta time to retry a destination increase too much,
    # set it to a maximum, and try the destination again
    d.add_failure()
    d.add_failure()
    d.add_failure(long_ago)
    # Pretend the delta seconds was already set to a bit more than
    # half the maximum.
    d._delta_seconds_retry = (MAX_SECONDS_RETRY_DESTINATION / 2) + 1
    assert d._are_last_attempts_failures()
    assert d._is_last_try_old_enough()
    assert d.is_functional()
    assert d._delta_seconds_retry == MAX_SECONDS_RETRY_DESTINATION
