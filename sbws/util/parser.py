import sbws.commands.cleanup
import sbws.commands.client
import sbws.commands.generate
import sbws.commands.init
import sbws.commands.pwgen
import sbws.commands.server
import sbws.commands.stats
from sbws import version

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import os


def _default_dot_sbws_dname():
    home = os.path.expanduser('~')
    return os.path.join(home, '.sbws')


def create_parser():
    p = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument(
        '--version', action='version', help='sbws version',
        version='%(prog)s {}'.format(version))
    p.add_argument(
        '-v', '--verbose', action='count', default=0,
        help='Increase log level verbosity from the configured value')
    p.add_argument(
        '-q', '--quiet', action='count', default=0,
        help='Decrease log level verbosity from the configured value')
    p.add_argument('-d', '--directory', default=_default_dot_sbws_dname(),
                   help='Name of the .sbws directory')
    sub = p.add_subparsers(dest='command')
    sbws.commands.cleanup.gen_parser(sub)
    sbws.commands.client.gen_parser(sub)
    sbws.commands.generate.gen_parser(sub)
    sbws.commands.init.gen_parser(sub)
    sbws.commands.pwgen.gen_parser(sub)
    sbws.commands.server.gen_parser(sub)
    sbws.commands.stats.gen_parser(sub)
    return p
