import os
import time
import logging
from filelock import FileLock

log = logging.getLogger(__name__)

G_PKG_DIR = os.path.abspath(os.path.dirname(__file__))
G_INIT_FILE_MAP = [
    # Specified as:
    #     (source, destination, type)
    # Where:
    #     - source is relative to the sbws/ directory
    #     - destination is relative to $HOME/.sbws/ directory (or whatever the
    #     user specified as their directory with --directory)
    #     - type is 'file', and ideally type 'dir' will be supported in the
    #     future as needed
]

# Minimum and maximum number of bytes a client is allowed to request from a
# server. If these are changed, a WIRE_PROTO_VER bump is required, which also
# happens to require an sbws major version bump.
#
# Note for smart people and people who pull out Wireshark: Even if the client
# requests 1 byte, that request and the 1 byte response will each be carried
# over the Internet in 514 byte Tor cells. Theoretically we could bump the
# minimum request size up to ~498 bytes, but I see no reason why we should.
# Trying to hit the maximum cell size just makes sbws server send more, us read
# more, and it runs the risk of standards changing underneath us and sbws
# suddenly creating more than one cell.
MIN_REQ_BYTES = 1
MAX_REQ_BYTES = 1 * 1024 * 1024 * 1024  # 1 GiB
SOCKET_TIMEOUT = 60  # seconds


def is_initted(d):
    if not os.path.isdir(d):
        return False
    for _, fname, _ in G_INIT_FILE_MAP:
        fname = os.path.join(d, fname)
        if not os.path.exists(fname):
            return False
    conf_fname = os.path.join(d, 'config.ini')
    if not os.path.exists(conf_fname):
        return False
    return True


def fail_hard(*a, **kw):
    ''' Optionally log something to stdout ... and then exit as fast as
    possible '''
    log.error(*a, **kw)
    exit(1)


def time_now():
    '''
    Return the current time in seconds since 1970. This function exists to
    make testing easier

    :returns: Unix timestamp as a float
    '''
    return time.time()


def _log_level_string_to_int(s):
    if s == 'debug':
        return 4
    elif s == 'info':
        return 3
    elif s == 'notice':
        return 2
    elif s == 'warn':
        return 1
    elif s == 'error':
        return 0
    fail_hard('Unknown log level:', s)


def _log_level_int_to_string(i):
    if i >= 4:
        return 'debug'
    elif i == 3:
        return 'info'
    elif i == 2:
        return 'notice'
    elif i == 1:
        return 'warn'
    else:
        return 'error'


def lock_directory(dname):
    '''
    Holds a lock on a file in **dname** so that other sbws processes/threads
    won't try to read/write while we are reading/writing in this directory.

    >>> with lock_directory(dname):
    >>>     # do things while you have the lock
    >>> # no longer have lock

    :param str dname: Name of directory we want to obtain a lock for
    :retrurns: the FileLock context manager for you to use in a with statement
    '''
    assert os.path.isdir(dname)
    return FileLock(os.path.join(dname, 'lockfile'))
