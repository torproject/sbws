from sbws.util.parser import create_parser
from sbws.util.config import get_config
from sbws.lib.resultdump import ResultError
from sbws.lib.resultdump import ResultSuccess
from sbws.lib.resultdump import Result
from sbws.lib.resultdump import write_result_to_datadir
import sbws.core.init
import sbws.core.stats
from datetime import date
import os
import time
import logging


def init_directory(dname):
    p = create_parser()
    args = p.parse_args('-d {} -vvvv init'.format(dname).split())
    conf = get_config(args)
    sbws.core.init.main(args, conf)


def add_single_stale_result(dname):
    r = ResultError(
        Result.Relay('DEADBEEF1111', 'CowSayWhat', '127.0.0.1'),
        ['DEADBEEF1111', 'BEADDEEF2222'],
        '127.0.1.1', 'SBWSclient', t=19950216)
    dd = os.path.join(str(dname), 'datadir')
    os.makedirs(dd)
    write_result_to_datadir(r, dd)


def add_single_fresh_result(dname):
    r = ResultError(
        Result.Relay('DEADBEEF1111', 'CowSayWhat', '127.0.0.1'),
        ['DEADBEEF1111', 'BEADDEEF2222'],
        '127.0.1.1', 'SBWSclient', t=time.time())
    dd = os.path.join(str(dname), 'datadir')
    os.makedirs(dd)
    write_result_to_datadir(r, dd)


def add_two_fresh_results(dname):
    r1 = ResultError(
        Result.Relay('DEADBEEF1111', 'CowSayWhat', '127.0.0.1'),
        ['DEADBEEF1111', 'BEADDEEF2222'],
        '127.0.1.1', 'SBWSclient', t=time.time())
    r2 = ResultSuccess(
        [1, 2, 3], [{'amount': 100, 'duration': 1}],
        Result.Relay('DEADBEEF1111', 'CowSayWhat', '127.0.0.1'),
        ['DEADBEEF1111', 'BEADDEEF2222'],
        '127.0.1.1', 'SBWSclient', t=time.time())
    dd = os.path.join(str(dname), 'datadir')
    os.makedirs(dd)
    write_result_to_datadir(r1, dd)
    write_result_to_datadir(r2, dd)


def test_stats_uninitted(tmpdir, caplog):
    '''
    An un-initialized .sbws directory should fail hard and exit immediately
    '''
    p = create_parser()
    args = p.parse_args('-d {} -vvvv stats'.format(tmpdir).split())
    conf = get_config(args)
    try:
        sbws.core.stats.main(args, conf)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    assert 'Sbws isn\'t initialized. Try sbws init' == \
        caplog.records[-1].getMessage()


def test_stats_initted(tmpdir, caplog):
    '''
    An initialized but rather empty .sbws directory should fail about missing
    ~/.sbws/datadir
    '''
    init_directory(tmpdir)
    p = create_parser()
    args = p.parse_args('-d {} -vvvv stats'.format(tmpdir).split())
    conf = get_config(args)
    try:
        sbws.core.stats.main(args, conf)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    assert '{}/datadir does not exist'.format(tmpdir) == \
        caplog.records[-1].getMessage()


def test_stats_stale_result(tmpdir, caplog):
    '''
    An initialized .sbws directory with no fresh results should say so and
    exit cleanly
    '''
    init_directory(tmpdir)
    add_single_stale_result(tmpdir)
    p = create_parser()
    args = p.parse_args('-d {} -vvvv stats'.format(tmpdir).split())
    conf = get_config(args)
    sbws.core.stats.main(args, conf)
    assert 'No fresh results' == caplog.records[-1].getMessage()


def test_stats_fresh_result(tmpdir, capsys, caplog):
    '''
    An initialized .sbws directory with a fresh error result should have some
    boring stats and exit cleanly
    '''
    caplog.set_level(logging.DEBUG)
    init_directory(tmpdir)
    add_single_fresh_result(tmpdir)
    p = create_parser()
    args = p.parse_args(
        '-d {} -vvvv stats --error-types'.format(tmpdir).split())
    conf = get_config(args)
    sbws.core.stats.main(args, conf)
    captured = capsys.readouterr()
    lines = captured.out.strip().split('\n')
    needed_output_lines = [
        '1 relays have recent results',
        'Average 0.00 successful measurements per relay',
        '0 success results and 1 error results',
    ]
    for needed_line in needed_output_lines:
        assert needed_line in lines
    lines = [l.getMessage() for l in caplog.records]
    needed_log_lines = [
        'Read 1 lines from {}/{}/{}.txt'.format(
            tmpdir, 'datadir', date.fromtimestamp(time.time())),
        'Keeping 1/1 results',
    ]
    for needed_line in needed_log_lines:
        assert needed_line in lines


def test_stats_fresh_results(tmpdir, capsys, caplog):
    '''
    An initialized .sbws directory with a fresh error and fresh success should
    have some exciting stats and exit cleanly
    '''
    caplog.set_level(logging.DEBUG)
    init_directory(tmpdir)
    add_two_fresh_results(tmpdir)
    p = create_parser()
    args = p.parse_args(
        '-d {} -vvvv stats --error-types'.format(tmpdir).split())
    conf = get_config(args)
    sbws.core.stats.main(args, conf)
    needed_output_lines = [
        '1 relays have recent results',
        '1 success results and 1 error results',
        'Average 1.00 successful measurements per relay',
        '1/2 (50.00%) results were error-misc',
    ]
    captured = capsys.readouterr()
    lines = captured.out.strip().split('\n')
    for needed_line in needed_output_lines:
        assert needed_line in lines
    lines = [l.getMessage() for l in caplog.records]
    needed_log_lines = [
        'Read 2 lines from {}/{}/{}.txt'.format(
            tmpdir, 'datadir', date.fromtimestamp(time.time())),
        'Keeping 2/2 results',
        'Found a _ResultType.Error for the first time',
        'Found a _ResultType.Success for the first time',
    ]
    for needed_line in needed_log_lines:
        assert needed_line in lines
