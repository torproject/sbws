from sbws.globals import (G_INIT_FILE_MAP, is_initted, fail_hard)
from argparse import ArgumentDefaultsHelpFormatter
import os
import shutil


def gen_parser(sub):
    p = sub.add_parser('init', formatter_class=ArgumentDefaultsHelpFormatter)


def main(args, log_):
    global log
    log = log_
    if is_initted(os.getcwd()):
        fail_hard('Directory already seems to be initted')

    dotdir = os.path.join(os.getcwd(), '.sbws')
    os.makedirs(dotdir, exist_ok=True)

    for src, dst, ftype in G_INIT_FILE_MAP:
        log.info(dst, '({})'.format(ftype))
        if ftype == 'file':
            try:
                shutil.copy(src, dst)
            except PermissionError as e:
                log.warn('Unable to create {}: {}'.format(dst, e))
        else:
            fail_hard('Cannot init ftype', ftype)
