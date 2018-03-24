import sbws.commands.client
import sbws.commands.server
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


VERSION = '0.0.1'


def create_parser():
    p = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    sub = p.add_subparsers(dest='command')
    sbws.commands.client.gen_parser(sub)
    sbws.commands.server.gen_parser(sub)
    return p


def main():
    parser = create_parser()
    args = parser.parse_args()
    def_args = [args]
    def_kwargs = {}
    known_commands = {
        'client': {'f': sbws.commands.client.main,
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
