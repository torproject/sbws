from sbws.util.filelock import FileLock
import os
import json


class State:
    _ALLOWED_TYPES = (int, float, str, bool, type(None))

    def __init__(self, fname):
        self._fname = fname
        self._state = self._read()

    def _read(self):
        with FileLock(self._fname):
            if not os.path.exists(self._fname):
                return {}
            with open(self._fname, 'rt') as fd:
                return json.load(fd)

    def _write(self):
        with FileLock(self._fname):
            with open(self._fname, 'wt') as fd:
                return json.dump(self._state, fd)

    def __len__(self):
        self._state = self._read()
        return self._state.__len__()

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
        self._state = self._read()
        self._state.__setitem__(key, value)
        self._write()

    def __iter__(self):
        self._state = self._read()
        return self._state.__iter__()

    def __contains__(self, item):
        self._state = self._read()
        return self._state.__contains__(item)
