import sbws.core.cleanup
import sbws.core.scanner
import sbws.core.generate
import sbws.core.init
import sbws.core.pwgen
import sbws.core.server
import sbws.core.stats
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
    p.add_argument('--log-level',
                   choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                   help='Override the sbws log level')
    p.add_argument('-d', '--directory', default=_default_dot_sbws_dname(),
                   help='Name of the .sbws directory')
    sub = p.add_subparsers(dest='command')
    sbws.core.cleanup.gen_parser(sub)
    sbws.core.scanner.gen_parser(sub)
    sbws.core.generate.gen_parser(sub)
    sbws.core.init.gen_parser(sub)
    sbws.core.pwgen.gen_parser(sub)
    sbws.core.server.gen_parser(sub)
    sbws.core.stats.gen_parser(sub)
    return p
