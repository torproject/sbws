from sbws.globals import (is_initted, fail_hard, touch_file)
from sbws.util.config import get_user_example_config
from sbws.util.userquery import query_yes_no
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

    # Create config.log.ini ####
    touch_file(os.path.join(args.directory, 'config.log.ini'))

    # Create config.ini ####
    fname = os.path.join(args.directory, 'config.ini')
    if os.path.exists(fname) and not os.path.isfile(fname):
        fail_hard('Don\'t know how to handle %s existing as a non-file', fname)
    if os.path.isfile(fname) and not query_yes_no(
            'Is it okay to overwrite {}?'.format(fname), default=None):
        fail_hard('Cannot continue')
    c = get_user_example_config()
    if 'paths' not in c:
        c['paths'] = {}
    c['paths']['sbws_home'] = args.directory
    log.info('Creating %s based on example config', fname)
    with open(fname, 'wt') as fd:
        c.write(fd)
