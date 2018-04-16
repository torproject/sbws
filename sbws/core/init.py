from sbws.globals import (is_initted, fail_hard, touch_file)
from sbws.util.config import get_user_example_config
from argparse import ArgumentDefaultsHelpFormatter
import os
import logging

log = logging.getLogger(__name__)


def gen_parser(sub):
    d = 'Initialize a directory so sbws can use it for configuration, '\
        'data storage, etc. A common default directory is ~/.sbws but check '\
        'the output of sbws -h to verify.'
    sub.add_parser('init', formatter_class=ArgumentDefaultsHelpFormatter,
                   description=d)


def main(args, conf):
    if is_initted(args.directory):
        fail_hard('Directory already seems to be initted')

    if not os.path.isdir(args.directory):
        log.info('Creating %s', args.directory)
        os.makedirs(args.directory, exist_ok=False)

    touch_file(os.path.join(args.directory, 'config.log.ini'))
    config_fname = os.path.join(args.directory, 'config.ini')
    c = get_user_example_config()
    c['paths']['sbws_home'] = args.directory
    log.info('Creating %s based on example config', config_fname)
    with open(config_fname, 'wt') as fd:
        c.write(fd)
