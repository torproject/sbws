"""Util functions to cleanup disk space."""
import types

from sbws.util.filelock import DirectoryLock
from sbws.globals import fail_hard
from sbws.util.timestamp import unixts_to_dt_obj
from argparse import ArgumentDefaultsHelpFormatter
from datetime import datetime
from datetime import timedelta
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
                          '%s', fname, extensions)
                continue
            # using file modification time instead of parsing the name
            # of the file.
            filedt = unixts_to_dt_obj(
                os.stat(fname, follow_symlinks=False).st_mtime)
            if filedt < oldest_day:
                yield fname


def _delete_files(dname, files, dry_run=True):
    """Delete the files passed as argument."""
    assert os.path.isdir(dname)
    assert isinstance(files, types.GeneratorType)
    with DirectoryLock(dname):
        for fname in files:
            log.info('Deleting %s', fname)
            assert os.path.commonprefix([dname, fname]) == dname
            if not dry_run:
                os.remove(fname)


def _compress_files(dname, files, dry_run=True):
    """Compress the files passed as argument."""
    assert os.path.isdir(dname)
    assert isinstance(files, types.GeneratorType)
    with DirectoryLock(dname):
        for fname in files:
            log.info('Compressing %s', fname)
            assert os.path.commonprefix([dname, fname]) == dname
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


def _check_validity_periods_results(
        data_period, compress_after_days, delete_after_days):
    if compress_after_days - 2 < data_period:
        fail_hard(
            'For safetly, cleanup/data_files_compress_after_days (%d) must be '
            'at least 2 days larger than general/data_period (%d)',
            compress_after_days, data_period)
    if delete_after_days < compress_after_days:
        fail_hard(
            'cleanup/data_files_delete_after_days (%d) must be the same or '
            'larger than cleanup/data_files_compress_after_days (%d)',
            delete_after_days, compress_after_days)
    if compress_after_days / 2 < data_period:
        log.warning(
            'cleanup/data_files_compress_after_days (%d) is less than twice '
            'general/data_period (%d). For ease of parsing older results '
            'if necessary, it is recommended to make '
            'data_files_compress_after_days at least twice the data_period.',
            compress_after_days, data_period)
    return True


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
                                                  ['.v3bw', '.gz'])
    _delete_files(v3bw_dname, files_to_delete, dry_run=args.dry_run)
    files_to_compress = _get_files_mtime_older_than(v3bw_dname,
                                                    compress_after_days,
                                                    ['.v3bw'])
    # when dry_run is true, compress will also show all the files that
    # would have been deleted, since they are not really deleted
    _compress_files(v3bw_dname, files_to_compress, dry_run=args.dry_run)


def _clean_result_files(args, conf):
    datadir = conf['paths']['datadir']
    if not os.path.isdir(datadir):
        fail_hard('%s does not exist', datadir)
    data_period = conf.getint('general', 'data_period')
    compress_after_days = conf.getint(
        'cleanup', 'data_files_compress_after_days')
    delete_after_days = conf.getint(
        'cleanup', 'data_files_delete_after_days')
    _check_validity_periods_results(
        data_period, compress_after_days, delete_after_days)

    # first delete so that the files to be deleted are not compressed first
    files_to_delete = _get_files_mtime_older_than(
        datadir, delete_after_days, ['.txt', '.gz'])
    _delete_files(datadir, files_to_delete, dry_run=args.dry_run)

    # when dry_run is true, compress will also show all the files that
    # would have been deleted, since they are not really deleted
    files_to_compress = _get_files_mtime_older_than(
        datadir, compress_after_days, ['.txt'])
    _compress_files(datadir, files_to_compress, dry_run=args.dry_run)


def main(args, conf):
    '''
    Main entry point in to the cleanup command.

    :param argparse.Namespace args: command line arguments
    :param configparser.ConfigParser conf: parsed config files
    '''
    datadir = conf.getpath('paths', 'datadir')
    if not os.path.isdir(datadir):
        fail_hard('%s does not exist', datadir)

    if not args.no_results:
        _clean_result_files(args, conf)

    if not args.no_v3bw:
        _clean_v3bw_files(args, conf)
