from sbws.util.filelock import FileLock
import os
import json


class State:
    """
    `json` wrapper to read a json file every time it gets a key and to write
    to the file every time a key is set.

    Every time a key is got or set, the file is locked, to atomically access
    and update the file across threads and across processes.

    >>> state = State('foo.state')
    >>> # state == {}

    >>> state['linux'] = True
    >>> # 'foo.state' now exists on disk with the JSON for {'linux': True}

    >>> # We read 'foo.state' from disk in order to get the most up-to-date
    >>> #     state info. Pretend another process has updated 'linux' to be
    >>> #     False
    >>> state['linux']
    >>> # returns False

    >>> # Pretend another process has added the user's age to the state file.
    >>> #     As before, we read the state file from disk for the most
    >>> #     up-to-date info.
    >>> state['age']
    >>> # Returns 14

    >>> # We now set their name. We read the state file first, set the option,
    >>> #     and then write it out.
    >>> state['name'] = 'John'

    >>> # We can do many of the same things with a State object as with a dict
    >>> for key in state: print(key)
    >>> # Prints 'linux', 'age', and 'name'

    """

    def __init__(self, fname):
        self._fname = fname
        self._state = self._read()

    def _read(self):
        if not os.path.exists(self._fname):
            return {}
        with FileLock(self._fname):
            with open(self._fname, 'rt') as fd:
                return json.load(fd)

    def _write(self):
        with FileLock(self._fname):
            with open(self._fname, 'wt') as fd:
                return json.dump(self._state, fd, indent=4)

    def __len__(self):
        self._state = self._read()
        return self._state.__len__()

    def get(self, key, d=None):
        """
        Implements a dictionary ``get`` method reading and locking
        a json file.
        """
        self._state = self._read()
        return self._state.get(key, d)

    def __getitem__(self, key):
        self._state = self._read()
        return self._state.__getitem__(key)

    def __delitem__(self, key):
        self._state = self._read()
        self._state.__delitem__(key)
        self._write()

    def __setitem__(self, key, value):
        # NOTE: important, read the file before setting the key,
        # otherwise if other instances are creating other keys, they're lost.
        self._state = self._read()
        self._state.__setitem__(key, value)
        self._write()

    def __iter__(self):
        self._state = self._read()
        return self._state.__iter__()

    def __contains__(self, item):
        self._state = self._read()
        return self._state.__contains__(item)

    def count(self, k):
        """
        Returns the length if the key value is a list
        or the sum of number if the key value is a list of list
        or the key value
        or None if the state doesn't have the key.
        """
        if self.get(k):
            if isinstance(self._state[k], list):
                if isinstance(self._state[k][0], list):
                    return sum(map(lambda x: x[1], self._state[k]))
                return len(self._state[k])
            return self.get(k)
        return None
