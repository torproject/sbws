import os
import fcntl
import logging
from sbws.globals import fail_hard

log = logging.getLogger(__name__)


class _FLock:
    def __init__(self, lock_fname):
        self._lock_fname = lock_fname
        self._fd = None

    def __enter__(self):
        mode = os.O_RDWR | os.O_CREAT | os.O_TRUNC
        self._fd = os.open(self._lock_fname, mode)
        log.debug('Going to lock %s', self._lock_fname)
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX)
        except OSError as e:
            fail_hard('We couldn\'t call flock. Are you on an unsupported '
                      'platform? Error: %s', e)
        log.debug('Received lock %s', self._lock_fname)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fd is not None:
            log.debug('Releasing lock %s', self._lock_fname)
            os.close(self._fd)


class DirectoryLock(_FLock):
    '''
    Holds a lock on a file in **dname** so that other sbws processes/threads
    won't try to read/write while we are reading/writing in this directory.

    >>> with DirectoryLock(dname):
    >>>     # do some reading/writing in dname
    >>> # no longer have the lock

    Note: The directory must already exist.

    :param str dname: Name of directory for which we want to obtain a lock
    '''
    def __init__(self, dname):
        assert os.path.isdir(dname)
        lock_fname = os.path.join(dname, '.lockfile')
        super().__init__(lock_fname)


class FileLock(_FLock):
    '''
    Holds a lock on **fname** so that other sbws processes/threads
    won't try to read/write while we are reading/writing this file.

    >>> with FileLock(fname):
    >>>     # do some reading/writing of fname
    >>> # no longer have the lock

    :param str fname: Name of the file for which we want to obtain a lock
    '''
    def __init__(self, fname):
        lock_fname = fname + '.lockfile'
        super().__init__(lock_fname)
