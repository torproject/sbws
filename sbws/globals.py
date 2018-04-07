import os
from sbws.lib.pastlylogger import PastlyLogger


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
MIN_REQ_BYTES = 1
MAX_REQ_BYTES = 50 * 1024 * 1024  # 50 MiB, tentatively XXX github #11
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


def fail_hard(*s, log=None):
    ''' Optionally log something to stdout ... and then exit as fast as
    possible '''
    if s:
        if log:
            log.error(*s)
        else:
            print(*s)
    exit(1)


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


def make_logger(args, conf):
    def get_logger(level, default):
        def_file = '/dev/stdout'
        common_kwargs = {'log_threads': True, 'default': default}
        if level == 'debug':
            return PastlyLogger(debug=def_file, overwrite=['debug'],
                                **common_kwargs)
        if level == 'info':
            return PastlyLogger(info=def_file, overwrite=['info'],
                                **common_kwargs)
        if level == 'notice':
            return PastlyLogger(notice=def_file, overwrite=['notice'],
                                **common_kwargs)
        if level == 'warn':
            return PastlyLogger(warn=def_file, overwrite=['warn'],
                                **common_kwargs)
        if level == 'error':
            return PastlyLogger(error=def_file, overwrite=['error'],
                                **common_kwargs)
        else:
            fail_hard('Unknown log level', level)
    level_str = conf.get('general', 'log_level')
    default_level_str = level_str
    level = _log_level_string_to_int(level_str)
    level = level + args.verbose - args.quiet
    level_str = _log_level_int_to_string(level)
    return get_logger(level_str, default_level_str)
