import sbws.commands.client
import sbws.commands.generate
import sbws.commands.init
import sbws.commands.server
from sbws.globals import make_logger
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


VERSION = '0.0.1'


def create_parser():
    p = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument(
        '-v', '--verbose', action='count', default=0,
        help='Increase log level verbosity from the configured value')
    p.add_argument(
        '-q', '--quiet', action='count', default=0,
        help='Decrease log level verbosity from the configured value')
    sub = p.add_subparsers(dest='command')
    sbws.commands.client.gen_parser(sub)
    sbws.commands.generate.gen_parser(sub)
    sbws.commands.init.gen_parser(sub)
    sbws.commands.server.gen_parser(sub)
    return p


def main():
    parser = create_parser()
    args = parser.parse_args()
    log = make_logger(args)
    def_args = [args, log]
    def_kwargs = {}
    known_commands = {
        'client': {'f': sbws.commands.client.main,
                   'a': def_args, 'kw': def_kwargs},
        'generate': {'f': sbws.commands.generate.main,
                     'a': def_args, 'kw': def_kwargs},
        'init': {'f': sbws.commands.init.main,
                 'a': def_args, 'kw': def_kwargs},
        'server': {'f': sbws.commands.server.main,
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
