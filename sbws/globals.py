import os
import logging

log = logging.getLogger(__name__)


def is_initted(d):
    if not os.path.isdir(d):
        log.debug('%s not initialized: %s doesn\'t exist', d, d)
        return False
    conf_fnames = [os.path.join(d, 'config.ini'),
                   os.path.join(d, 'config.log.ini')]
    for fname in conf_fnames:
        if not os.path.isfile(fname):
            log.debug('%s not initialized: missing %s', d, fname)
            return False
    log.debug('%s seems initialized.', d)
    return True


def fail_hard(*a, **kw):
    ''' Log something ... and then exit as fast as possible '''
    log.critical(*a, **kw)
    exit(1)


def touch_file(fname, times=None):
    '''
    If **fname** exists, update its last access and modified times to now. If
    **fname** does not exist, create it. If **times** are specified, pass them
    to os.utime for use.

    :param str fname: Name of file to update or create
    :param tuple times: 2-tuple of floats for access time and modified time
        respectively
    '''
    log.debug('Touching %s', fname)
    with open(fname, 'a') as fd:
        os.utime(fd.fileno(), times=times)
