import os
import logging
import socket

log = logging.getLogger(__name__)

RESULT_VERSION = 4
WIRE_VERSION = 1
SPEC_VERSION = '1.1.0'

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
    # Because we need things from full server descriptors (namely for now: the
    # bandwidth line)
    'UseMicrodescriptors': '0',
}

PKG_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_CONFIG_PATH = os.path.join(PKG_DIR, 'config.default.ini')
DEFAULT_LOG_CONFIG_PATH = os.path.join(PKG_DIR, 'config.log.default.ini')
USER_CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.sbws.ini')

SOCKET_TIMEOUT = 60  # seconds

SBWS_SCALE_CONSTANT = 7500
TORFLOW_SCALING = 1
SBWS_SCALING = 2
TORFLOW_BW_MARGIN = 0.05
TORFLOW_OBS_LAST = 0
TORFLOW_OBS_MEAN = 1
TORFLOW_OBS_DECAYING = 3
TORFLOW_ROUND_DIG = 3

BW_LINE_SIZE = 510


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
