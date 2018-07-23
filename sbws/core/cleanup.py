"""Util functions to cleanup disk space."""
import types

from sbws.util.filelock import DirectoryLock
from sbws.globals import (fail_hard, is_initted)
from sbws.util.timestamp import unixts_to_dt_obj
from argparse import ArgumentDefaultsHelpFormatter
from datetime import datetime
from datetime import timedelta
import re
import os
import gzip
import shutil
import logging
import time

log = logging.getLogger(__name__)


def gen_parser(sub):
    '''
    Helper function for the broader argument parser generating code that adds
    in all the possible command line arguments for the cleanup command.

    :param argparse._SubParsersAction sub: what to add a sub-parser to
    '''
    d = 'Compress and delete results and/or v3bw files old files.' \
        'Configuration options are read to determine which are old files'
    p = sub.add_parser('cleanup', description=d,
                       formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('--dry-run', action='store_true',
                   help='Don\'t actually compress or delete anything')
    p.add_argument('--no-results', action='store_true',
                   help='Do not clean results files')
    p.add_argument('--no-v3bw', action='store_true',
                   help='Do not clean v3bw files')


def _get_files_mtime_older_than(dname, days_delta, extensions):
    """Return files which modification time is older than days_delta
    and which extension is one of the extensions."""
    assert os.path.isdir(dname)
    assert isinstance(days_delta, int)
    assert isinstance(extensions, list)
    for ext in extensions:
        assert isinstance(ext, str)
        assert ext[0] == '.'
    # Determine oldest allowed date
    today = datetime.utcfromtimestamp(time.time())
    oldest_day = today - timedelta(days=days_delta)
    for root, dirs, files in os.walk(dname):
        for f in files:
            fname = os.path.join(root, f)
            _, ext = os.path.splitext(fname)
            if ext not in extensions:
                log.debug('Ignoring %s because its extension is not in '
                          '%s', fname, ext)
                continue
            # using file modification time instead of parsing the name
            # of the file.
            filedt = unixts_to_dt_obj(
                os.stat(fname, follow_symlinks=False).st_mtime)
            if filedt < oldest_day and os.path.splitext:
                yield fname


def _get_older_files_than(dname, num_days_ago, extensions):
    assert os.path.isdir(dname)
    assert isinstance(num_days_ago, int)
    assert isinstance(extensions, list)
    for ext in extensions:
        assert isinstance(ext, str)
        assert ext[0] == '.'
    # Determine oldest allowed date
    today = datetime.utcfromtimestamp(time.time())
    oldest_day = today - timedelta(days=num_days_ago)
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
            match = regex.match(fname)
            if not match:
                log.debug('Ignoring %s because it doesn\'t look like '
                          'YYYY-MM-DD', fname)
                continue
            d = datetime(*[int(n) for n in match.group(1).split('-')])
            if d < oldest_day:
                yield fname


def _delete_files(dname, files, dry_run=True):
    """Delete the files passed as argument."""
    assert os.path.isdir(dname)
    assert isinstance(files, types.GeneratorType)
    with DirectoryLock(dname):
        for fname in files:
            log.info('Deleting %s', fname)
            if not dry_run:
                os.remove(fname)


def _remove_rotten_files(datadir, rotten_days, dry_run=True):
    assert os.path.isdir(datadir)
    assert isinstance(rotten_days, int)
    # Hold the lock for basically the entire time just in case someone else
    # moves files between when we get the list of files and when we try to
    # delete them.
    with DirectoryLock(datadir):
        for fname in _get_older_files_than(datadir, rotten_days,
                                           ['.txt', '.txt.gz']):
            log.info('Deleting %s', fname)
            if not dry_run:
                os.remove(fname)


def _compress_files(dname, files, dry_run=True):
    """Compress the files passed as argument."""
    assert os.path.isdir(dname)
    assert isinstance(files, types.GeneratorType)
    with DirectoryLock(dname):
        for fname in files:
            log.info('Compressing %s', fname)
            if dry_run:
                continue
            with open(fname, 'rt') as in_fd:
                out_fname = fname + '.gz'
                with gzip.open(out_fname, 'wt') as out_fd:
                    shutil.copyfileobj(in_fd, out_fd)
            os.remove(fname)


def _compress_stale_files(datadir, stale_days, dry_run=True):
    assert os.path.isdir(datadir)
    assert isinstance(stale_days, int)
    # Hold the lock for basically the entire time just in case someone else
    # moves files between when we get the list of files and when we try to
    # compress them.
    with DirectoryLock(datadir):
        for fname in _get_older_files_than(datadir, stale_days, ['.txt']):
            log.info('Compressing %s', fname)
            if dry_run:
                continue
            with open(fname, 'rt') as in_fd:
                out_fname = fname + '.gz'
                with gzip.open(out_fname, 'wt') as out_fd:
                    shutil.copyfileobj(in_fd, out_fd)
            os.remove(fname)


def _check_validity_periods_v3bw(compress_after_days, delete_after_days):
    if 1 <= compress_after_days and compress_after_days < delete_after_days:
        return True
    fail_hard("v3bw files should only be compressed after 1 day and deleted "
              "after a bigger number of days.")


def _clean_v3bw_files(args, conf):
    v3bw_dname = conf['paths']['v3bw_dname']
    if not os.path.isdir(v3bw_dname):
        fail_hard('%s does not exist', v3bw_dname)
    compress_after_days = conf.getint('cleanup',
                                      'v3bw_files_compress_after_days')
    delete_after_days = conf.getint('cleanup',
                                    'v3bw_files_delete_after_days')
    _check_validity_periods_v3bw(compress_after_days, delete_after_days)
    # first delete so that the files to be deleted are not compressed first
    files_to_delete = _get_files_mtime_older_than(v3bw_dname,
                                                  delete_after_days,
                                                  ['.v3bw'])
    _delete_files(v3bw_dname, files_to_delete, dry_run=args.dry_run)
    files_to_compress = _get_files_mtime_older_than(v3bw_dname,
                                                    compress_after_days,
                                                    ['.v3bw'])
    # when dry_run is true, compress will also show all the files that
    # would have been deleted, since they are not really deleted
    _compress_files(v3bw_dname, files_to_compress, dry_run=args.dry_run)


def main(args, conf):
    '''
    Main entry point in to the cleanup command.

    :param argparse.Namespace args: command line arguments
    :param configparser.ConfigParser conf: parsed config files
    '''
    if not is_initted(args.directory):
        fail_hard('Sbws isn\'t initialized. Try sbws init')

    if args.no_results and args.no_v3bw:
        fail_hard('Nothing to clean.')

    if not args.no_results:
        datadir = conf['paths']['datadir']
        if not os.path.isdir(datadir):
            fail_hard('%s does not exist', datadir)

        fresh_days = conf.getint('general', 'data_period')
        stale_days = conf.getint('cleanup', 'stale_days')
        rotten_days = conf.getint('cleanup', 'rotten_days')
        if stale_days - 2 < fresh_days:
            fail_hard('For safetly, cleanup/stale_days (%d) must be at least '
                      '2 days larger than general/data_period (%d)',
                      stale_days, fresh_days)
        if rotten_days < stale_days:
            fail_hard('cleanup/rotten_days (%d) must be the same or larger '
                      'than cleanup/stale_days (%d)', rotten_days, stale_days)

        if stale_days / 2 < fresh_days:
            log.warning(
                'cleanup/stale_days (%d) is less than twice '
                'general/data_period (%d). For ease of parsing older results '
                'if necessary, it is recommended to make stale_days at least '
                'twice the data_period.', stale_days, fresh_days)

        _remove_rotten_files(datadir, rotten_days, dry_run=args.dry_run)
        _compress_stale_files(datadir, stale_days, dry_run=args.dry_run)

    if not args.no_v3bw:
        _clean_v3bw_files(args, conf)
