import os
import logging
import platform

from requests import __version__ as requests_version
from stem import __version__ as stem_version

from sbws import __version__


from collections import OrderedDict


log = logging.getLogger(__name__)

RESULT_VERSION = 4
WIRE_VERSION = 1
SPEC_VERSION = '1.2.0'

# This is a dictionary of torrc options we always want to set when launching
# Tor and that do not depend on any runtime configuration
# Options that are known at runtime (from configuration file) are added
# in utils/stem.py launch_tor
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
# Options that need to be set at runtime.
TORRC_RUNTIME_OPTIONS = {
    # The scanner builds the circuits to download the data itself,
    # so do not let Tor to build them.
    '__DisablePredictedCircuits': '1',
    # The scanner attach the streams to the circuit itself,
    # so do not let Tor to attache them.
    '__LeaveStreamsUnattached': '1',
}
# Options that can be set at runtime and can fail with some Tor versions
# The ones that fail will be ignored..
TORRC_OPTIONS_CAN_FAIL = OrderedDict({
    # Since currently scanner anonymity is not the goal, ConnectionPadding
    # is disable to do not send extra traffic
    'ConnectionPadding': '0'
    })

PKG_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_CONFIG_PATH = os.path.join(PKG_DIR, 'config.default.ini')
DEFAULT_LOG_CONFIG_PATH = os.path.join(PKG_DIR, 'config.log.default.ini')
USER_CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.sbws.ini')
SUPERVISED_USER_CONFIG_PATH = "/etc/sbws/sbws.ini"
SUPERVISED_RUN_DPATH = "/run/sbws/tor"

SOCKET_TIMEOUT = 60  # seconds
TIMEOUT_MEASUREMENTS = 60 * 3  # 3 minutes

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

# With the new KeyValues in #29591, the lines are greater than 510
# Tor already accept lines of any size, but leaving the limit anyway.
BW_LINE_SIZE = 1022

# RelayList, ResultDump, v3bwfile
# For how many seconds in the past the relays and measurements data is keep/
# considered valid.
# This is currently set by default in config.default.ini as ``date_period``,
# and used in ResultDump and v3bwfile.
# In a future refactor, constants in config.default.ini should be moved here,
# or calculated in settings, so that there's no need to pass the configuration
# to all the functions.
MEASUREMENTS_PERIOD = 5 * 24 * 60 * 60

# Metadata to send in every requests, so that data servers can know which
# scanners are using them.
# In Requests these keys are case insensitive.
HTTP_HEADERS = {
    # This would be ignored if changing to HTTP/2
    'Connection': 'keep-alive',
    # Needs to get Tor version from the controller
    'User-Agent': 'sbws/{} ({}) Python/{} Requests/{} Stem/{} Tor/'.format(
                    __version__, platform.platform(),
                    platform.python_version(),
                    requests_version, stem_version),
    # Organization defined names (:rfc:`7239`)
    # Needs to get the nickname from the user config file.
    'Tor-Bandwidth-Scanner-Nickname': '{}',
    'Tor-Bandwidth-Scanner-UUID': '{}',
    # In case of including IP address.
    # 'Forwarded': 'for={}'  # IPv6 part, if there's
    }
# In the case of having ipv6 it's concatenated to forwarder.
IPV6_FORWARDED = ', for="[{}]"'

HTTP_GET_HEADERS = {
    'Range': '{}',
    'Accept-Encoding': 'identity',
}
DESTINATION_VERIFY_CERTIFICATE = True
# This number might need adjusted depending on the percentage of circuits and
# HTTP requests failures.
# While the scanner can not recover from some/all failing destionations,
# set a big number so that it continues trying.
MAXIMUM_NUMBER_DESTINATION_FAILURES = 100


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
