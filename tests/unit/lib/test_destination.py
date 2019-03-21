"""Unit tests for sbws.lib.destination."""
from datetime import datetime, timedelta

from sbws.lib import destination


def test_destination_is_functional():
    eight_hours_ago = datetime.utcnow() - timedelta(hours=8)
    four_hours_ago = datetime.utcnow() - timedelta(hours=4)
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)

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
    d.add_failure(two_hours_ago)
    assert d._are_last_attempts_failures()
    assert not d._is_last_try_old_enough()
    assert not d.is_functional()

    # But if the last failure was 4h ago, try to use it again
    # And last failure was 4h ago
    d.add_failure(four_hours_ago)
    assert d._is_last_try_old_enough()
    assert d.is_functional()

    # If last failure was 8h ago, try to use it again again
    d.add_failure(eight_hours_ago)
    assert d._is_last_try_old_enough()
    assert d.is_functional()

    # Whenever it does not fail again, reset the time to try again
    # on 3 consecutive failures
    d.add_success()
    assert not d._are_last_attempts_failures()
    assert d.is_functional()
    # And the delta to try is resetted
    assert not d._is_last_try_old_enough()
