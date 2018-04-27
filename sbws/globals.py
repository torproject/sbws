import os
import logging

log = logging.getLogger(__name__)

RESULT_VERSION = 1
WIRE_VERSION = 1
SPEC_VERSION = '1.1.0'

PKG_DIR = os.path.abspath(os.path.dirname(__file__))

SOCKET_TIMEOUT = 60  # seconds

# Minimum and maximum number of bytes a scanner is allowed to request from a
# server. If these are changed, a WIRE_VERSION bump is required, which also
# happens to require an sbws major version bump.
#
# Note for smart people and people who pull out Wireshark: Even if the scanner
# requests 1 byte, that request and the 1 byte response will each be carried
# over the Internet in 514 byte Tor cells. Theoretically we could bump the
# minimum request size up to ~498 bytes, but I see no reason why we should.
# Trying to hit the maximum cell size just makes sbws server send more, us read
# more, and it runs the risk of standards changing underneath us and sbws
# suddenly creating more than one cell.
MIN_REQ_BYTES = 1
MAX_REQ_BYTES = 1 * 1024 * 1024 * 1024  # 1 GiB


def is_initted(d):
    if not os.path.isdir(d):
        log.debug('%s not initialized: %s doesn\'t exist', d, d)
        return False
    conf_fnames = [os.path.join(d, 'config.ini'),
                   os.path.join(d, 'config.log.ini')]
    for fname in conf_fnames:
        if not os.path.isfile(fname):
            log.debug('%s not initialized: missing %s', d, fname)
            return False
    log.debug('%s seems initialized.', d)
    return True


def fail_hard(*a, **kw):
    ''' Log something ... and then exit as fast as possible '''
    log.critical(*a, **kw)
    exit(1)


def touch_file(fname, times=None):
    '''
    If **fname** exists, update its last access and modified times to now. If
    **fname** does not exist, create it. If **times** are specified, pass them
    to os.utime for use.

    :param str fname: Name of file to update or create
    :param tuple times: 2-tuple of floats for access time and modified time
        respectively
    '''
    log.debug('Touching %s', fname)
    with open(fname, 'a') as fd:
        os.utime(fd.fileno(), times=times)
