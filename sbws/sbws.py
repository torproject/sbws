import sbws.commands.cleanup
import sbws.commands.client
import sbws.commands.generate
import sbws.commands.init
import sbws.commands.pwgen
import sbws.commands.server
import sbws.commands.stats
from sbws.util.config import get_config
from sbws.util.config import validate_config
from sbws.util.parser import create_parser
from sbws.globals import make_logger


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
        'cleanup': {'f': sbws.commands.cleanup.main,
                    'a': def_args, 'kw': def_kwargs},
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
