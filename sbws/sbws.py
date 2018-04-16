import sbws.core.cleanup
import sbws.core.client
import sbws.core.generate
import sbws.core.init
import sbws.core.pwgen
import sbws.core.server
import sbws.core.stats
from sbws.util.config import get_config
from sbws.util.config import validate_config
from sbws.util.config import configure_logging
from sbws.util.parser import create_parser
import logging

log = logging.getLogger(__name__)


def _adjust_log_level(args, conf):
    if not args.log_level:
        return
    conf['logger_sbws']['level'] = args.log_level


def main():
    parser = create_parser()
    args = parser.parse_args()
    conf = get_config(args)
    _adjust_log_level(args, conf)
    conf_valid, conf_errors = validate_config(conf)
    if not conf_valid:
        for e in conf_errors:
            log.critical(e)
        exit(1)
    configure_logging(conf)
    def_args = [args, conf]
    def_kwargs = {}
    known_commands = {
        'cleanup': {'f': sbws.core.cleanup.main,
                    'a': def_args, 'kw': def_kwargs},
        'client': {'f': sbws.core.client.main,
                   'a': def_args, 'kw': def_kwargs},
        'generate': {'f': sbws.core.generate.main,
                     'a': def_args, 'kw': def_kwargs},
        'init': {'f': sbws.core.init.main,
                 'a': def_args, 'kw': def_kwargs},
        'pwgen': {'f': sbws.core.pwgen.main,
                  'a': def_args, 'kw': def_kwargs},
        'server': {'f': sbws.core.server.main,
                   'a': def_args, 'kw': def_kwargs},
        'stats': {'f': sbws.core.stats.main,
                  'a': def_args, 'kw': def_kwargs},
    }
    try:
        if args.command not in known_commands:
            parser.print_help()
        else:
            comm = known_commands[args.command]
            exit(comm['f'](*comm['a'], **comm['kw']))
    except KeyboardInterrupt:
        print('')
