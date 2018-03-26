import os
from sbws.lib.pastlylogger import PastlyLogger


G_PKG_DIR = os.path.abspath(os.path.dirname(__file__))
G_INIT_FILE_MAP = [
    # (source, destination, type)
    (os.path.join(G_PKG_DIR, 'passwords.txt.example'),
     'passwords.txt', 'file'),
]
log = None


def is_initted(d):
    dotdir = os.path.join(d, '.sbws')
    if not os.path.isdir(dotdir):
        return False
    for _, fname, _ in G_INIT_FILE_MAP:
        if not os.path.exists(fname):
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


def make_logger(args): # noqa
    def get_log_level_string(args):
        arg_level = 2
        if args.verbose:
            arg_level += args.verbose
        if args.quiet:
            arg_level -= args.quiet
        level = arg_level
        if level <= 0:
            return 'error'
        elif level == 1:
            return 'warn'
        elif level == 2:
            return 'notice'
        elif level == 3:
            return 'info'
        elif level >= 4:
            return 'debug'
        fail_hard('This should not have been reached.')

    def get_logger(level):
        def_file = '/dev/stdout'
        common_kwargs = {'log_threads': True}
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
    level = get_log_level_string(args)
    return get_logger(level)
