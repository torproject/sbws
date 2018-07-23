import os

import sbws.core.cleanup
import sbws.core.scanner
import sbws.core.generate
import sbws.core.stats
from sbws.util.config import get_config
from sbws.util.config import validate_config
from sbws.util.config import configure_logging
from sbws.util.parser import create_parser
from sbws import __version__ as version
from stem import __version__ as stem_version
from requests.__version__ import __version__ as requests_version
import platform
import logging

log = logging.getLogger(__name__)


def _ensure_dirs(conf):
    log.debug('Ensuring all dirs exists.')
    # it is not needed to check sbws_home dir, since the following
    # will create parent dirs too (in case they don't exist)
    os.makedirs(conf['paths']['datadir'], exist_ok=True)
    os.makedirs(conf['paths']['v3bw_dname'], exist_ok=True)
    os.makedirs(conf['paths']['log_dname'], exist_ok=True)


def _adjust_log_level(args, conf):
    if not args.log_level:
        return
    conf['logger_sbws']['level'] = args.log_level


def _get_startup_line():
    py_ver = platform.python_version()
    py_plat = platform.platform()
    return 'sbws %s with python %s on %s, stem %s, and requests %s' % \
        (version, py_ver, py_plat, stem_version, requests_version)


def main():
    parser = create_parser()
    args = parser.parse_args()
    conf = get_config(args)
    _ensure_dirs(conf)
    _adjust_log_level(args, conf)
    conf_valid, conf_errors = validate_config(conf)
    if not conf_valid:
        for e in conf_errors:
            log.critical(e)
        exit(1)
    configure_logging(args, conf)
    def_args = [args, conf]
    def_kwargs = {}
    known_commands = {
        'cleanup': {'f': sbws.core.cleanup.main,
                    'a': def_args, 'kw': def_kwargs},
        'scanner': {'f': sbws.core.scanner.main,
                    'a': def_args, 'kw': def_kwargs},
        'generate': {'f': sbws.core.generate.main,
                     'a': def_args, 'kw': def_kwargs},
        'stats': {'f': sbws.core.stats.main,
                  'a': def_args, 'kw': def_kwargs},
    }
    try:
        if args.command not in known_commands:
            parser.print_help()
        else:
            log.info(_get_startup_line())
            comm = known_commands[args.command]
            exit(comm['f'](*comm['a'], **comm['kw']))
    except KeyboardInterrupt:
        print('')
