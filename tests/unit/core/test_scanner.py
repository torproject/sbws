"""Unit tests for scanner.py."""
import pytest

from sbws.core.scanner import result_putter


def test_result_putter(sbwshome_only_datadir, result_success, rd, end_event):
    if rd is None:
        pytest.skip("ResultDump is None")
    # Put one item in the queue
    callback = result_putter(rd)
    callback(result_success)
    assert rd.queue.qsize() == 1

    # Make queue maxsize 1, so that it'll be full after the first callback.
    # The second callback will wait 1 second, then the queue will be empty
    # again.
    rd.queue.maxsize = 1
    callback(result_success)
    # after putting 1 result, the queue will be full
    assert rd.queue.qsize() == 1
    assert rd.queue.full()
    # it's still possible to put another results, because the callback will
    # wait 1 second and the queue will be empty again.
    callback(result_success)
    assert rd.queue.qsize() == 1
    assert rd.queue.full()
    end_event.set()
