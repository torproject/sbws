from sbws.globals import G_INIT_FILE_MAP
from ..lib.pastlylogger import PastlyLogger
from argparse import ArgumentDefaultsHelpFormatter
import os
import shutil

log = None


def fail_hard(*s):
    ''' Optionally log something to stdout ... and then exit as fast as
    possible '''
    if s:
        log.error(*s)
    exit(1)


def gen_parser(sub):
    p = sub.add_parser('init', formatter_class=ArgumentDefaultsHelpFormatter)


def main(args):
    global log
    log = PastlyLogger(debug='/dev/stdout', overwrite=['debug'],
                       log_threads=True)

    dotdir = os.path.join(os.getcwd(), '.sbws')
    if os.path.exists(dotdir):
        fail_hard('Directory already seems to be initted')
    os.makedirs(dotdir)

    for src, dst, ftype in G_INIT_FILE_MAP:
        log.info(dst, '({})'.format(ftype))
        if ftype == 'file':
            shutil.copy(src, dst)
        else:
            fail_hard('Cannot init ftype', ftype)
