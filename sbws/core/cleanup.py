from sbws.util.filelock import DirectoryLock
from sbws.globals import (fail_hard, is_initted)
from argparse import ArgumentDefaultsHelpFormatter
from datetime import datetime
from datetime import timedelta
import re
import os
import gzip
import shutil
import logging
import time

from sbws.util.timestamp import unixts_to_dt_obj

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

    p.add_argument('--v3bw', action='store_true', help='Clean also v3bw files')


def _get_older_files_than(dname, time_delta, extensions, is_v3bw=False):
    assert os.path.isdir(dname)
    assert isinstance(time_delta, int)
    assert isinstance(extensions, list)
    for ext in extensions:
        assert isinstance(ext, str)
        assert ext[0] == '.'
    # Determine oldest allowed date
    today = datetime.utcfromtimestamp(time.time())
    oldest_day = today - timedelta(days=time_delta)
    if is_v3bw:
        oldest = today - timedelta(minutes=time_delta)
    # Compile a regex that can extract a date from a file name that looks like
    # /path/to/foo/YYYY-MM-DD*.extension
    extensions = [re.escape(e) for e in extensions]
    day_part = '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
    regex = re.compile(r'^.*/({}).*({})$'
                       .format(day_part, '|'.join(extensions)))
    # Walk through all files in the given dname, find files that match the
    # regex, and yield the ones that contain a date in the file name that is
    # too old.
    for root, dirs, files in os.walk(dname):
        for f in files:
            fname = os.path.join(root, f)
            if is_v3bw:  # or (v3bw_ext not in fname)
                # not forcing files to have correct names just the extension
                _, ext = os.path.splitext(fname)
                if ext not in ['.v3bw']:
                    log.debug('Ignoring %s because it doesn\'t have extension '
                              '%s', fname, ext)
                    continue
                dt = unixts_to_dt_obj(os.path.getmtime(fname))
                if dt < oldest and os.path.splitext:
                    yield fname
            else:
                match = regex.match(fname)
                if not match:
                    log.debug('Ignoring %s because it doesn\'t look like '
                              'YYYY-MM-DD', fname)
                    continue
                d = datetime(*[int(n) for n in match.group(1).split('-')])
                if d < oldest_day:
                    yield fname


def _remove_rotten_files(datadir, rotten_days, dry_run=True, is_v3bw=False):
    assert os.path.isdir(datadir)
    assert isinstance(rotten_days, int)
    # Hold the lock for basically the entire time just in case someone else
    # moves files between when we get the list of files and when we try to
    # delete them.
    exts = ['.txt', '.txt.gz'] if not is_v3bw else ['.v3bw']
    with DirectoryLock(datadir):
        for fname in _get_older_files_than(datadir, rotten_days, exts,
                                           is_v3bw):
            log.info('Deleting %s', fname)
            if not dry_run:
                os.remove(fname)


def _compress_stale_files(datadir, stale_days, dry_run=True, is_v3bw=False):
    assert os.path.isdir(datadir)
    assert isinstance(stale_days, int)
    # Hold the lock for basically the entire time just in case someone else
    # moves files between when we get the list of files and when we try to
    # compress them.
    exts = ['.txt', '.txt.gz'] if not is_v3bw else ['.v3bw']
    with DirectoryLock(datadir):
        for fname in _get_older_files_than(datadir, stale_days, exts,
                                           is_v3bw):
            log.info('Compressing %s', fname)
            if dry_run:
                continue
            with open(fname, 'rt') as in_fd:
                out_fname = fname + '.gz'
                with gzip.open(out_fname, 'wt') as out_fd:
                    shutil.copyfileobj(in_fd, out_fd)
            os.remove(fname)


def _check_validity_periods(valid, stale, rotten):
    if stale - 2 < valid:
        fail_hard('For safetly, cleanup/stale_* (%d) must be at least 2 '
                  'days larger than general/data_period or general/valid_ * '
                  '(%d)', stale, valid)
    if rotten < stale:
        fail_hard('cleanup/rotten_* (%d) must be the same or larger than '
                  'cleanup/stale_* (%d)', rotten, stale)

    if stale / 2 < valid:
        log.warning(
            'cleanup/stale_ (%d) is less than twice '
            'general/data_period or general/valid_*(%d). '
            'For ease of parsing older results '
            'if necessary, it is recommended to make stale at least '
            'twice the data_period.', stale, valid)


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
        fail_hard('%s does not exist', datadir)

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

    if args.v3bw:
        v3bw_dir = conf['paths']['v3bw_dname']
        if not os.path.isdir(datadir):
            fail_hard('%s does not exist', v3bw_dir)
        valid = conf.getint('general', 'valid_mins_v3bw_files')
        stale = conf.getint('cleanup', 'stale_mins_v3bw_files')
        rotten = conf.getint('cleanup', 'rotten_mins_v3bw_files')
        _check_validity_periods(valid, stale, rotten)
        _remove_rotten_files(v3bw_dir, rotten, dry_run=args.dry_run,
                             is_v3bw=True)
        _compress_stale_files(v3bw_dir, stale, dry_run=args.dry_run,
                              is_v3bw=True)
