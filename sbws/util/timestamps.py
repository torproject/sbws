"""Util classes to manipulate sequences of datetime timestamps.

Optionally update also a state file.

"""
# Workarounds to store datetimes for objects because they are not compossed
# by other objects nor stored in a database with a creation datetime.
import collections
from datetime import datetime, timedelta
import logging

from sbws.util.timestamp import is_old

log = logging.getLogger(__name__)


class DateTimeSeq(collections.deque):
    """Store and manage a datetime sequence and optionally a state file."""

    def __init__(self, iterable=[], maxlen=None, state=None, state_key=None):
        self._maxlen = maxlen
        self._items = collections.deque(iterable, maxlen)
        self._state = state
        self._state_key = state_key

    def _remove_old(self):
        self._items = collections.deque(
            filter(lambda x: not is_old(x), self._items), maxlen=self._maxlen
        )

    def update(self, dt=None):
        self._remove_old()
        self._items.append(dt or datetime.utcnow().replace(microsecond=0))
        if self._state is not None and self._state_key:
            self._state[self._state_key] = list(self._items)
        return list(self._items)

    def last(self):
        if len(self._items) > 0:
            return self._items[-1]
        return datetime.utcnow().replace(microsecond=0) - timedelta(hour=1)

    def list(self):
        return list(self._items)

    def __len__(self):
        return len(self._items)


class DateTimeIntSeq(collections.deque):
    """
    Store and manage a sequence of lists composed of a datetime and an int.

    Optionally store and manage an state file.
    """

    def __init__(self, iterable=[], maxlen=None, state=None, state_key=None):
        self._maxlen = maxlen
        self._items = collections.deque(iterable, maxlen)
        self._state = state
        self._state_key = state_key

    def _remove_old(self):
        self._items = collections.deque(
            filter(lambda x: not is_old(x[0]), self._items),
            maxlen=self._maxlen,
        )

    def update(self, dt=None, number=0):
        self._remove_old()
        # Because json serializes tuples to lists, use list instead of tuple
        # to facilitate comparisons.
        self._items.append(
            [dt or datetime.utcnow().replace(microsecond=0), number]
        )
        if self._state is not None and self._state_key:
            self._state[self._state_key] = list(self._items)
        return list(self._items)

    def last(self):
        if len(self._items) > 0:
            return self._items[-1]
        return datetime.utcnow().replace(microsecond=0) - timedelta(hour=1)

    def list(self):
        return list(self._items)

    def __len__(self):
        return sum(map(lambda x: x[1], self._items))
