import os.path

import sbws.core.stats
from tests.unit.globals import monotonic_time
from unittest.mock import patch
import logging


def test_stats_initted(sbwshome_empty, args, conf, caplog):
    '''
    An initialized but rather empty .sbws directory should fail about missing
    ~/.sbws/datadir
    '''
    try:
        sbws.core.stats.main(args, conf)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    assert '{}/datadir does not exist'.format(
        os.path.abspath(sbwshome_empty)) == caplog.records[-1].getMessage()


def test_stats_stale_result(args, conf, caplog,
                            sbwshome_success_result):
    '''
    An initialized .sbws directory with no fresh results should say so and
    exit cleanly
    '''
    caplog.set_level(logging.DEBUG)
    sbws.core.stats.main(args, conf)
    assert 'No fresh results' == caplog.records[-1].getMessage()


@patch('time.time')
def test_stats_fresh_result(time_mock, sbwshome_error_result, args, conf,
                            capsys, caplog):
    '''
    An initialized .sbws directory with a fresh error result should have some
    boring stats and exit cleanly
    '''
    args.error_types = False
    start = 1529232278
    time_mock.side_effect = monotonic_time(start=start)
    sbws.core.stats.main(args, conf)
    captured = capsys.readouterr()
    lines = captured.out.strip().split('\n')
    assert '1 relays have recent results' in lines[0]
    # FIXME
    # needed_output_lines = [
    #     '1 relays have recent results',
    #     'Mean 0.00 successful measurements per relay',
    #     '0 success results and 1 error results',
    # ]
    # for needed_line in needed_output_lines:
    #     assert needed_line in lines
    # lines = [l.getMessage() for l in caplog.records]
    # needed_log_lines = [
    #     'Keeping 1/1 read lines from {}/{}/{}.txt'.format(
    #         sbwshome_error_result, 'datadir', '2018-06-17'),
    #     'Keeping 1/1 results after removing old ones',
    # ]
    # for needed_line in needed_log_lines:
    #     assert needed_line in lines


@patch('time.time')
def test_stats_fresh_results(time_mock, sbwshome_success_result_two_relays,
                             args, conf, capsys, caplog):
    '''
    An initialized .sbws directory with a fresh error and fresh success should
    have some exciting stats and exit cleanly
    '''
    caplog.set_level(logging.DEBUG)
    start = 1529232278
    time_mock.side_effect = monotonic_time(start=start)
    sbws.core.stats.main(args, conf)
    captured = capsys.readouterr()
    lines = captured.out.strip().split('\n')
    assert '1 relays have recent results' in lines[0]
    # FIXME
    # needed_output_lines = [
    #     '1 relays have recent results',
    #     '1 success results and 1 error results',
    #     'Mean 1.00 successful measurements per relay',
    #     '1/2 (50.00%) results were error-misc',
    # ]
    # for needed_line in needed_output_lines:
    #     assert needed_line in lines
    # lines = [l.getMessage() for l in caplog.records]
    # needed_log_lines = [
    #     'Keeping 2/2 read lines from {}/{}/{}.txt'.format(
    #         sbwshome_success_result_two_relays, 'datadir',
    #         datetime.utcfromtimestamp(time.time()).date()),
    #     'Keeping 2/2 results after removing old ones',
    #     'Found a _ResultType.Error for the first time',
    #     'Found a _ResultType.Success for the first time',
    # ]
    # for needed_line in needed_log_lines:
    #     assert needed_line in lines
