import os
import logging

log = logging.getLogger(__name__)

RESULT_VERSION = 4
WIRE_VERSION = 1
SPEC_VERSION = '1.2.0'

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
    # useful logging options for clients that don't care about anonymity
    'SafeLogging': '0',
    'LogTimeGranularity': '1',
    'ProtocolWarnings': '1',
}

TORRC_RUNTIME_OPTIONS = {
    '__DisablePredictedCircuits': '1',
    '__LeaveStreamsUnattached': '1',
}

PKG_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_CONFIG_PATH = os.path.join(PKG_DIR, 'config.default.ini')
DEFAULT_LOG_CONFIG_PATH = os.path.join(PKG_DIR, 'config.log.default.ini')
USER_CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.sbws.ini')
SUPERVISED_USER_CONFIG_PATH = "/etc/sbws/sbws.ini"
SUPERVISED_RUN_DPATH = "/run/sbws/tor"

SOCKET_TIMEOUT = 60  # seconds

SBWS_SCALE_CONSTANT = 7500
TORFLOW_SCALING = 1
SBWS_SCALING = 2
TORFLOW_BW_MARGIN = 0.05
TORFLOW_OBS_LAST = 0
TORFLOW_OBS_MEAN = 1
TORFLOW_OBS_DECAYING = 3
TORFLOW_ROUND_DIG = 3
PROP276_ROUND_DIG = 2
DAY_SECS = 86400
NUM_MIN_RESULTS = 2
MIN_REPORT = 60
# Maximum difference between the total consensus bandwidth and the total in
# in the bandwidth lines in percentage
MAX_BW_DIFF_PERC = 50

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
