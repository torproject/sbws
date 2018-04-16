from sbws.globals import (fail_hard, is_initted, time_now, lock_directory)
from argparse import ArgumentDefaultsHelpFormatter
from datetime import date
from datetime import timedelta
from glob import glob
import os
import gzip
import shutil
import logging

log = logging.getLogger(__name__)


def gen_parser(sub):
    '''
    Helper function for the broader argument parser generating code that adds
    in all the possible command line arguments for the cleanup command.

    :param argparse._SubParsersAction sub: what to add a sub-parser to
    '''
    d = 'Compress data files that are no longer fresh and delete data files '\
        'that stopped being fresh a long time ago'
    p = sub.add_parser('cleanup', description=d,
                       formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('--dry-run', action='store_true',
                   help='Don\'t actually compress or delete anything')


def _get_older_files_than(dname, num_days_ago, extensions):
    assert os.path.isdir(dname)
    assert isinstance(num_days_ago, int)
    assert isinstance(extensions, list)
    for ext in extensions:
        assert isinstance(ext, str)
        assert ext[0] == '.'
    # First get all files that *probably* start with the format YYYY-MM-DD*.txt
    # in all dirs in the dname recursively
    all_fnames = set()
    for ext in extensions:
        pattern = os.path.join(dname, '**', '*-*-*{}'.format(ext))
        for fname in glob(pattern, recursive=True):
            all_fnames.add(fname)
    # Figure out what files are too new
    new_fnames = set()
    today = date.fromtimestamp(time_now())
    oldest_day = today - timedelta(days=num_days_ago)
    working_day = oldest_day
    while working_day <= today:
        for ext in extensions:
            pattern = os.path.join(
                dname, '**', '{}*{}'.format(working_day, ext))
            for fname in glob(pattern, recursive=True):
                new_fnames.add(fname)
        working_day += timedelta(days=1)
    # Then return the files that are in all_fnames but not in new_fnames, as
    # these will the be ones that are too old
    return sorted([f for f in all_fnames if f not in new_fnames])


def _remove_rotten_files(datadir, rotten_days, dry_run=True):
    assert os.path.isdir(datadir)
    assert isinstance(rotten_days, int)
    # Hold the lock for basically the entire time just in case someone else
    # moves files between when we get the list of files and when we try to
    # delete them.
    with lock_directory(datadir):
        fnames = _get_older_files_than(datadir, rotten_days,
                                       ['.txt', '.txt.gz'])
        for fname in fnames:
            log.info('Deleting %s', fname)
            if not dry_run:
                os.remove(fname)


def _compress_stale_files(datadir, stale_days, dry_run=True):
    assert os.path.isdir(datadir)
    assert isinstance(stale_days, int)
    # Hold the lock for basically the entire time just in case someone else
    # moves files between when we get the list of files and when we try to
    # compress them.
    with lock_directory(datadir):
        fnames = _get_older_files_than(datadir, stale_days, ['.txt'])
        for fname in fnames:
            log.info('Compressing %s', fname)
            if dry_run:
                continue
            with open(fname, 'rt') as in_fd:
                out_fname = fname + '.gz'
                with gzip.open(out_fname, 'wt') as out_fd:
                    shutil.copyfileobj(in_fd, out_fd)
            os.remove(fname)


def main(args, conf):
    '''
    Main entry point in to the cleanup command.

    :param argparse.Namespace args: command line arguments
    :param configparser.ConfigParser conf: parsed config files
    '''
    if not is_initted(args.directory):
        fail_hard('Sbws isn\'t initialized. Try sbws init')

    datadir = conf['paths']['datadir']
    if not os.path.isdir(datadir):
        fail_hard(datadir, 'does not exist')

    fresh_days = conf.getint('general', 'data_period')
    stale_days = conf.getint('cleanup', 'stale_days')
    rotten_days = conf.getint('cleanup', 'rotten_days')
    if stale_days - 2 < fresh_days:
        fail_hard('For safetly, cleanup/stale_days (%d) must be at least 2 '
                  'days larger than general/data_period (%d)', stale_days,
                  fresh_days)
    if rotten_days < stale_days:
        fail_hard('cleanup/rotten_days (%d) must be the same or larger than '
                  'cleanup/stale_days (%d)', rotten_days, stale_days)

    if stale_days / 2 < fresh_days:
        log.warning(
            'cleanup/stale_days (%d) is less than twice '
            'general/data_period (%d). For ease of parsing older results '
            'if necessary, it is recommended to make stale_days at least '
            'twice the data_period.', stale_days, fresh_days)

    _remove_rotten_files(datadir, rotten_days, dry_run=args.dry_run)
    _compress_stale_files(datadir, stale_days, dry_run=args.dry_run)
