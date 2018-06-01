from sbws.util.config import get_config
from sbws.globals import touch_file
import sbws.core.cleanup
from tests.unit.globals import monotonic_time
from unittest.mock import patch
import logging
import os

log = logging.getLogger(__name__)


def test_cleanup_no_dotsbws(tmpdir, caplog, parser):
    caplog.set_level(logging.DEBUG)
    dotsbws = tmpdir
    args = parser.parse_args(
        '-d {} --log-level DEBUG cleanup'.format(dotsbws).split())
    conf = get_config(args)
    try:
        sbws.core.cleanup.main(args, conf)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    assert 'Try sbws init' in caplog.records[-1].getMessage()


def test_cleanup_no_datadir(empty_dotsbws, caplog, parser):
    dotsbws = empty_dotsbws
    args = parser.parse_args(
        '-d {} --log-level DEBUG cleanup'.format(dotsbws.name).split())
    conf = get_config(args)
    try:
        sbws.core.cleanup.main(args, conf)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    dd = conf['paths']['datadir']
    assert '{} does not exist'.format(dd) in caplog.records[-1].getMessage()


def test_cleanup_small_stale(empty_dotsbws_datadir, caplog, parser):
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} --log-level DEBUG cleanup'.format(dotsbws.name).split())
    conf = get_config(args)
    conf['general']['data_period'] = '1'
    conf['cleanup']['stale_days'] = '2'
    conf['cleanup']['rotten_days'] = '3'
    try:
        sbws.core.cleanup.main(args, conf)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    assert 'cleanup/stale_days (2) must be at least 2 days larger than ' +\
        'general/data_period (1)' in caplog.records[-1].getMessage()


def test_cleanup_small_rotten(empty_dotsbws_datadir, caplog, parser):
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} --log-level DEBUG cleanup'.format(dotsbws.name).split())
    conf = get_config(args)
    conf['general']['data_period'] = '1'
    conf['cleanup']['stale_days'] = '5'
    conf['cleanup']['rotten_days'] = '4'
    try:
        sbws.core.cleanup.main(args, conf)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    assert 'cleanup/rotten_days (4) must be the same or larger than ' +\
        'cleanup/stale_days (5)' in caplog.records[-1].getMessage()


def test_cleanup_medium_stale(empty_dotsbws_datadir, caplog, parser):
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} --log-level DEBUG cleanup'.format(dotsbws.name).split())
    conf = get_config(args)
    conf['general']['data_period'] = '10'
    conf['cleanup']['stale_days'] = '19'
    conf['cleanup']['rotten_days'] = '50'
    sbws.core.cleanup.main(args, conf)
    assert 'cleanup/stale_days (19) is less than twice ' +\
        'general/data_period (10).' in caplog.records[-1].getMessage()


@patch('time.time')
def test_cleanup_only_compress_stale(time_mock, empty_dotsbws_datadir, caplog,
                                     parser):
    caplog.set_level(logging.DEBUG)
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} --log-level DEBUG cleanup'.format(dotsbws.name).split())
    conf = get_config(args)
    conf['general']['data_period'] = '1'
    conf['cleanup']['stale_days'] = '10'
    conf['cleanup']['rotten_days'] = str(365*2)
    now = 1041379200  # 1,041,379,200 is 1 Jan 2003 00:00:00 UTC
    time_mock.side_effect = monotonic_time(start=now)
    j = os.path.join
    dd = j(dotsbws.name, 'datadir')
    sub_a = j(dd, 'a')
    sub_b = j(dd, 'b')
    sub_ab = j(dd, 'a', 'b')
    for dname in [sub_a, sub_b, sub_ab]:
        os.makedirs(dname, exist_ok=True)
    should_compress_fnames = [
        j(dd, '2002-01-01aaaa.txt'),
        j(sub_a, '2002-10-01bbbb.txt'),
        j(sub_b, '2002-10-10-cccc.txt'),
        j(sub_a, '2002-10-10.dddd.txt'),
        j(sub_ab, '2002-11-30.txt'),
    ]
    should_ignore_fnames = [
        j(sub_b, '2002-10-10.nottxt'),  # wrong ext, should be ignored
        j(sub_a, '200j-10-10.txt'),  # not YYYY-MM-DD*.txt, should be ignored
    ]
    for fname in should_ignore_fnames + should_compress_fnames:
        touch_file(fname)
    sbws.core.cleanup.main(args, conf)
    should_compress_fnames = [f + '.gz' for f in should_compress_fnames]
    expected_fnames = should_ignore_fnames + should_compress_fnames +\
        [os.path.join(dd, '.lockfile')]
    existing_fnames = []
    for root, dirs, files in os.walk(dd):
        for fname in files:
            existing_fnames.append(os.path.join(root, fname))
    expected_fnames.sort()
    existing_fnames.sort()
    assert expected_fnames == existing_fnames


@patch('time.time')
def test_cleanup_only_delete_rotten(time_mock, empty_dotsbws_datadir, caplog,
                                    parser):
    caplog.set_level(logging.DEBUG)
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} --log-level DEBUG cleanup'.format(dotsbws.name).split())
    conf = get_config(args)
    conf['general']['data_period'] = '1'
    conf['cleanup']['stale_days'] = '10'
    conf['cleanup']['rotten_days'] = str(365*2)
    now = 1041379200  # 1,041,379,200 is 1 Jan 2003 00:00:00 UTC
    time_mock.side_effect = monotonic_time(start=now)
    j = os.path.join
    dd = j(dotsbws.name, 'datadir')
    sub_a = j(dd, 'a')
    sub_b = j(dd, 'b')
    sub_ab = j(dd, 'a', 'b')
    for dname in [sub_a, sub_b, sub_ab]:
        os.makedirs(dname, exist_ok=True)
    should_delete_fnames = [
        j(dd, '2000-01-01aaaa.txt'),
        j(sub_a, '2000-10-01bbbb.txt'),
        j(sub_b, '2000-10-10-cccc.txt'),
        j(sub_a, '2000-10-10.dddd.txt'),
        j(sub_a, '2000-10-11.eeee.txt.gz'),
        j(dd, '2000-10-12.txt.gz'),
        j(sub_ab, '2000-11-30.txt'),
    ]
    should_ignore_fnames = [
        j(dd, '2002-12-31.txt'),  # too new, should be ignored
        j(dd, '2003-01-01.txt'),  # today, should be ignored
        j(dd, '2003-02-10.txt'),  # in the future, should be ignored
        j(sub_b, '2000-10-10.nottxt'),  # wrong ext, should be ignored
        j(sub_a, '200j-10-10.txt'),  # not YYYY-MM-DD*.txt, should be ignored
        j(dd, '1999-1*-11.txt.gz'),  # not YYYY-MM-DD*.txt.gz, should ignore
    ]
    for fname in should_ignore_fnames + should_delete_fnames:
        touch_file(fname)
    sbws.core.cleanup.main(args, conf)
    expected_fnames = should_ignore_fnames + [os.path.join(dd, '.lockfile')]
    existing_fnames = []
    for root, dirs, files in os.walk(dd):
        for fname in files:
            existing_fnames.append(os.path.join(root, fname))
    expected_fnames.sort()
    existing_fnames.sort()
    assert expected_fnames == existing_fnames


def test_cleanup_nothing_to_do(empty_dotsbws_datadir, caplog, parser):
    caplog.set_level(logging.DEBUG)
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} --log-level DEBUG cleanup'.format(dotsbws.name).split())
    conf = get_config(args)
    try:
        sbws.core.cleanup.main(args, conf)
    except Exception as e:
        assert None, 'Nothing bad should have happened, but this did: {}'\
            .format(e)


@patch('time.time')
def test_cleanup_compress_barely_stale(time_mock, empty_dotsbws_datadir,
                                       caplog, parser):
    caplog.set_level(logging.DEBUG)
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} --log-level DEBUG cleanup'.format(dotsbws.name).split())
    conf = get_config(args)
    conf['general']['data_period'] = '1'
    conf['cleanup']['stale_days'] = '10'
    conf['cleanup']['rotten_days'] = '30'
    now = 1443571200  # 1,443,571,200 is 30 Sep 2015 00:00:00 UTC
    time_mock.side_effect = monotonic_time(start=now)
    dd = os.path.join(dotsbws.name, 'datadir')
    fname_compress1 = os.path.join(dd, '2015-09-19.txt')
    fname_compress2 = os.path.join(dd, '2015-09-20.txt')
    fname_leave = os.path.join(dd, '2015-09-21.txt')
    touch_file(fname_compress1)
    touch_file(fname_compress2)
    touch_file(fname_leave)
    sbws.core.cleanup.main(args, conf)
    expected_fnames = [
        fname_compress1 + '.gz',
        fname_compress2 + '.gz',
        fname_leave,
        os.path.join(dd, '.lockfile'),
    ]
    existing_fnames = []
    for root, dirs, files in os.walk(dd):
        for fname in files:
            existing_fnames.append(os.path.join(root, fname))
    expected_fnames.sort()
    existing_fnames.sort()
    assert expected_fnames == existing_fnames


@patch('time.time')
def test_cleanup_delete_barely_rotten(time_mock, empty_dotsbws_datadir,
                                      caplog, parser):
    caplog.set_level(logging.DEBUG)
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} --log-level DEBUG cleanup'.format(dotsbws.name).split())
    conf = get_config(args)
    conf['general']['data_period'] = '1'
    conf['cleanup']['stale_days'] = '5'
    conf['cleanup']['rotten_days'] = '20'
    now = 1443571200  # 1,443,571,200 is 30 Sep 2015 00:00:00 UTC
    time_mock.side_effect = monotonic_time(start=now)
    dd = os.path.join(dotsbws.name, 'datadir')
    fname_rotten1 = os.path.join(dd, '2015-09-09.txt')
    fname_rotten2 = os.path.join(dd, '2015-09-10.txt')
    fname_leave = os.path.join(dd, '2015-09-11.txt')
    touch_file(fname_rotten1)
    touch_file(fname_rotten2)
    touch_file(fname_leave)
    sbws.core.cleanup.main(args, conf)
    expected_fnames = [
        fname_leave + '.gz',
        os.path.join(dd, '.lockfile'),
    ]
    existing_fnames = []
    for root, dirs, files in os.walk(dd):
        for fname in files:
            existing_fnames.append(os.path.join(root, fname))
    expected_fnames.sort()
    existing_fnames.sort()
    assert expected_fnames == existing_fnames
