from sbws.util.filelock import FileLock
import os
import json


class State:
    '''
    State allows one to atomically access and update a simple state file on
    disk across threads and across processes.

    To put it blunty, due to limited developer time and his inability to
    quickly find a way to safely access and update more complex data types
    (namely, collections like list, set, and dict), you may only store simple
    types of data as enumerated in _ALLOWED_TYPES. Keys must be strings.

    Data is stored as JSON on disk in the provided file file.

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
    '''
    _ALLOWED_TYPES = (int, float, str, bool, type(None))

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
        if not isinstance(key, str):
            raise TypeError(
                'Keys must be strings. %s is a %s' % (key, type(key)))
        self._state = self._read()
        return self._state.get(key, d)

    def __getitem__(self, key):
        if not isinstance(key, str):
            raise TypeError(
                'Keys must be strings. %s is a %s' % (key, type(key)))
        self._state = self._read()
        return self._state.__getitem__(key)

    def __delitem__(self, key):
        if not isinstance(key, str):
            raise TypeError(
                'Keys must be strings. %s is a %s' % (key, type(key)))
        self._state = self._read()
        self._state.__delitem__(key)
        self._write()

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError(
                'Keys must be strings. %s is a %s' % (key, type(key)))
        if type(value) not in State._ALLOWED_TYPES:
            raise TypeError(
                'May only store value with type in %s, not %s' %
                (State._ALLOWED_TYPES, type(value)))
        self._state.__setitem__(key, value)
        self._write()

    def __iter__(self):
        self._state = self._read()
        return self._state.__iter__()

    def __contains__(self, item):
        self._state = self._read()
        return self._state.__contains__(item)
