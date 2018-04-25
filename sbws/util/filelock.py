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
    def __init__(self, dname):
        assert os.path.isdir(dname)
        lock_fname = os.path.join(dname, '.lockfile')
        super().__init__(lock_fname)


class FileLock(_FLock):
    def __init__(self, fname):
        assert os.path.isdir(fname)
        lock_fname = fname + '.lockfile'
        super().__init__(lock_fname)
