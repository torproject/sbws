import os
import logging
import socket

log = logging.getLogger(__name__)

RESULT_VERSION = 2
WIRE_VERSION = 1
SPEC_VERSION = '1.1.0'

PKG_DIR = os.path.abspath(os.path.dirname(__file__))

SOCKET_TIMEOUT = 60  # seconds

# This is a dictionary of torrc options we always want to set when launching
# Tor and that do not depend on any runtime configuration
TORRC_STARTING_POINT = {
    # We will find out via the ControlPort and not setting something static
    # means a lower chance of conflict
    'SocksPort': 'auto',
    # Easier than password authentication
    'CookieAuthentication': '1',
    # To avoid path bias warnings
    'UseEntryGuards': '0',
}

TIMESTAMP_DT_FRMT = "%d-%m-%Y %H:%M:%S"


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


def resolve(hostname, ipv4_only=False, ipv6_only=False):
    assert not (ipv4_only and ipv6_only)
    ret = set()
    for result in socket.getaddrinfo(hostname, 0):
        fam, _, _, _, addr = result
        if fam == socket.AddressFamily.AF_INET6 and not ipv4_only:
            ret.add(addr[0])
        elif fam == socket.AddressFamily.AF_INET and not ipv6_only:
            ret.add(addr[0])
        else:
            assert None, 'Unknown address family {}'.format(fam)
    return list(ret)
