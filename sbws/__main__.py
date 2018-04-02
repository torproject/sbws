import sbws.commands.client
import sbws.commands.generate
import sbws.commands.init
import sbws.commands.pwgen
import sbws.commands.server
import sbws.commands.stats
from sbws.util.config import get_config
from sbws.util.config import validate_config
from sbws.globals import make_logger
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import os

VERSION = '0.1.0'


def _default_dot_sbws_dname():
    home = os.path.expanduser('~')
    return os.path.join(home, '.sbws')


def create_parser():
    p = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument(
        '-v', '--verbose', action='count', default=0,
        help='Increase log level verbosity from the configured value')
    p.add_argument(
        '-q', '--quiet', action='count', default=0,
        help='Decrease log level verbosity from the configured value')
    p.add_argument('-d', '--directory', default=_default_dot_sbws_dname(),
                   help='Name of the .sbws directory')
    sub = p.add_subparsers(dest='command')
    sbws.commands.client.gen_parser(sub)
    sbws.commands.generate.gen_parser(sub)
    sbws.commands.init.gen_parser(sub)
    sbws.commands.pwgen.gen_parser(sub)
    sbws.commands.server.gen_parser(sub)
    sbws.commands.stats.gen_parser(sub)
    return p


def _log_buffer():
    ''' Little helper for when you want to log some things before the
    PastlyLogger is created. use log_buf['add'] like you would print(), and
    use log_buf['dump'] to get all lines that were buffered as an iterable.

    >>> log_buf = _log_buffer()
    >>> log_buf['add']('Hello, world')
    >>> log_buf['add']('This is the second line')
    >>> for line in log_buf['dump']():
    >>>     print(line)

    '''
    buf = []

    def add(*s):
        buf.append(' '.join([str(_) for _ in s]))

    def dump():
        while len(buf):
            yield buf.pop(0)
    return {'add': add, 'dump': dump}


def main():
    log_buf = _log_buffer()
    parser = create_parser()
    args = parser.parse_args()
    conf = get_config(args, log_fn=log_buf['add'])
    log = make_logger(args, conf)
    for line in log_buf['dump']():
        log.debug(line)
    conf_valid, conf_errors = validate_config(conf)
    if not conf_valid:
        for e in conf_errors:
            log.error(e)
        exit(1)
    def_args = [args, conf, log]
    def_kwargs = {}
    known_commands = {
        'client': {'f': sbws.commands.client.main,
                   'a': def_args, 'kw': def_kwargs},
        'generate': {'f': sbws.commands.generate.main,
                     'a': def_args, 'kw': def_kwargs},
        'init': {'f': sbws.commands.init.main,
                 'a': def_args, 'kw': def_kwargs},
        'pwgen': {'f': sbws.commands.pwgen.main,
                  'a': def_args, 'kw': def_kwargs},
        'server': {'f': sbws.commands.server.main,
                   'a': def_args, 'kw': def_kwargs},
        'stats': {'f': sbws.commands.stats.main,
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
