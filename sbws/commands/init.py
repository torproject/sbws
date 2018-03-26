from sbws.globals import (G_INIT_FILE_MAP, is_initted, fail_hard)
from ..lib.pastlylogger import PastlyLogger
from argparse import ArgumentDefaultsHelpFormatter
import os
import shutil

log = None


def gen_parser(sub):
    p = sub.add_parser('init', formatter_class=ArgumentDefaultsHelpFormatter)


def main(args):
    global log
    log = PastlyLogger(debug='/dev/stdout', overwrite=['debug'],
                       log_threads=True)
    if is_initted(os.getcwd()):
        fail_hard('Directory already seems to be initted')

    dotdir = os.path.join(os.getcwd(), '.sbws')
    os.makedirs(dotdir, exist_ok=True)

    for src, dst, ftype in G_INIT_FILE_MAP:
        log.info(dst, '({})'.format(ftype))
        if ftype == 'file':
            shutil.copy(src, dst)
        else:
            fail_hard('Cannot init ftype', ftype)
