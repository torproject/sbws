# FIXME: all functions that depend on num lines should only use bandwith lines
# and not whole header bandwith lines, as every time we change headers,
# tests here would break
# import pytest

import sbws.core.generate
from sbws.util.config import get_config
from sbws.lib.resultdump import load_recent_results_in_datadir
from sbws.lib.resultdump import ResultSuccess
from sbws.lib.v3bwfile import NUM_LINES_HEADER_V110, V3BWLine
from sbws.util.timestamp import unixts_to_isodt_str
from statistics import median
import logging

log = logging.getLogger(__name__)


def test_generate_no_dotsbws(tmpdir, caplog, parser):
    caplog.set_level(logging.DEBUG)
    dotsbws = tmpdir
    args = parser.parse_args(
        '-d {} --log-level DEBUG generate'.format(dotsbws).split())
    conf = get_config(args)
    try:
        sbws.core.generate.main(args, conf)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    assert 'Try sbws init' in caplog.records[-1].getMessage()


def test_generate_no_datadir(empty_dotsbws, caplog, parser):
    dotsbws = empty_dotsbws
    args = parser.parse_args(
        '-d {} --log-level DEBUG generate --output /dev/stdout'
        .format(dotsbws.name).split())
    conf = get_config(args)
    try:
        sbws.core.generate.main(args, conf)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    dd = conf['paths']['datadir']
    assert '{} does not exist'.format(dd) in caplog.records[-1].getMessage()


def test_generate_bad_scale_constant(empty_dotsbws_datadir, caplog, parser):
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} --log-level DEBUG generate --scale-constant -1 '
        '--output /dev/stdout'.format(dotsbws.name).split())
    conf = get_config(args)
    try:
        sbws.core.generate.main(args, conf)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    assert '--scale-constant must be positive' in \
        caplog.records[-1].getMessage()


def test_generate_empty_datadir(empty_dotsbws_datadir, caplog, parser):
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} --log-level DEBUG generate --output /dev/stdout'
        .format(dotsbws.name).split())
    conf = get_config(args)
    sbws.core.generate.main(args, conf)
    assert 'No recent results' in caplog.records[-1].getMessage()


def test_generate_single_error(dotsbws_error_result, caplog, parser):
    caplog.set_level(logging.DEBUG)
    dotsbws = dotsbws_error_result
    args = parser.parse_args(
        '-d {} --log-level DEBUG generate --output /dev/stdout'
        .format(dotsbws.name).split())
    conf = get_config(args)
    sbws.core.generate.main(args, conf)
    dd = conf['paths']['datadir']
    for record in caplog.records:
        if 'Keeping 0/1 read lines from {}'.format(dd) in record.getMessage():
            break
    else:
        assert None, 'Unable to find log line indicating 0 success ' \
            'results in data file'
    assert 'No recent results' in caplog.records[-1].getMessage()


def test_generate_single_success_noscale(dotsbws_success_result, caplog,
                                         parser,  capfd):
    dotsbws = dotsbws_success_result
    args = parser.parse_args(
        '-d {} --log-level DEBUG generate --output /dev/stdout'
        .format(dotsbws.name).split())
    conf = get_config(args)
    sbws.core.generate.main(args, conf)
    dd = conf['paths']['datadir']
    # Here results is a dict
    results = load_recent_results_in_datadir(1, dd, success_only=False)
    assert isinstance(results, dict)
    res_len = sum([len(results[fp]) for fp in results])
    assert res_len == 1, 'There should be one result in the datadir'
    # And here we change it to a list
    results = [r for fp in results for r in results[fp]]
    result = results[0]
    assert isinstance(result, ResultSuccess), 'The one existing result '\
        'should be a success'
    captured = capfd.readouterr()
    stdout_lines = captured.out.strip().split('\n')
    assert len(stdout_lines) == 1 + NUM_LINES_HEADER_V110

    bw = round(median([dl['amount'] / dl['duration'] / 1024
                       for dl in result.downloads]))
    rtt = median([round(r * 1000) for r in result.rtts])
    bw_line = V3BWLine(result.fingerprint, bw, nick=result.nickname, rtt=rtt,
                       time=unixts_to_isodt_str(round(result.time)),
                       master_key_ed25519=result.master_key_ed25519,
                       success=1, error_circ=0, error_misc=0,
                       error_stream=0)
    assert stdout_lines[NUM_LINES_HEADER_V110] + '\n' == str(bw_line)


def test_generate_single_success_scale(dotsbws_success_result, parser,
                                       capfd):
    dotsbws = dotsbws_success_result
    args = parser.parse_args(
        '-d {} --log-level DEBUG generate --scale --output /dev/stdout'
        .format(dotsbws.name).split())
    conf = get_config(args)
    sbws.core.generate.main(args, conf)
    dd = conf['paths']['datadir']
    # Here results is a dict
    results = load_recent_results_in_datadir(1, dd, success_only=False)
    assert isinstance(results, dict)
    res_len = sum([len(results[fp]) for fp in results])
    assert res_len == 1, 'There should be one result in the datadir'
    # And here we change it to a list
    results = [r for fp in results for r in results[fp]]
    result = results[0]
    assert isinstance(result, ResultSuccess), 'The one existing result '\
        'should be a success'
    captured = capfd.readouterr()
    stdout_lines = captured.out.strip().split('\n')
    assert len(stdout_lines) == 1 + NUM_LINES_HEADER_V110

    bw = 7500
    rtt = median([round(r * 1000) for r in result.rtts])
    bw_line = V3BWLine(result.fingerprint, bw, nick=result.nickname, rtt=rtt,
                       time=unixts_to_isodt_str(round(result.time)),
                       master_key_ed25519=result.master_key_ed25519,
                       success=1, error_circ=0, error_misc=0,
                       error_stream=0)
    assert stdout_lines[NUM_LINES_HEADER_V110] + '\n' == str(bw_line)


def test_generate_single_relay_success_noscale(
        dotsbws_success_result_one_relay, parser, capfd):
    dotsbws = dotsbws_success_result_one_relay
    args = parser.parse_args(
        '-d {} --log-level DEBUG generate --output /dev/stdout'
        .format(dotsbws.name).split())
    conf = get_config(args)
    sbws.core.generate.main(args, conf)
    dd = conf['paths']['datadir']
    # Here results is a dict
    results = load_recent_results_in_datadir(1, dd, success_only=False)
    assert isinstance(results, dict)
    res_len = sum([len(results[fp]) for fp in results])
    assert res_len == 2, 'There should be two results in the datadir'
    # And here we change it to a list
    results = [r for fp in results for r in results[fp]]
    for result in results:
        assert isinstance(result, ResultSuccess), 'All existing results '\
            'should be a success'
    captured = capfd.readouterr()
    stdout_lines = captured.out.strip().split('\n')
    assert len(stdout_lines) == 1 + NUM_LINES_HEADER_V110

    speeds = [dl['amount'] / dl['duration'] / 1024
              for r in results for dl in r.downloads]
    speed = round(median(speeds))
    rtt = round(median([round(r * 1000) for r in result.rtts]))
    bw_line = V3BWLine(result.fingerprint, speed, nick=result.nickname,
                       rtt=rtt, master_key_ed25519=result.master_key_ed25519,
                       time=unixts_to_isodt_str(round(result.time)),
                       success=2, error_circ=0, error_misc=0,
                       error_stream=0)
    assert stdout_lines[NUM_LINES_HEADER_V110] + '\n' == str(bw_line)


def test_generate_single_relay_success_scale(
        dotsbws_success_result_one_relay, parser, capfd):
    dotsbws = dotsbws_success_result_one_relay
    args = parser.parse_args(
        '-d {} --log-level DEBUG generate --scale --output /dev/stdout'
        .format(dotsbws.name).split())
    conf = get_config(args)
    sbws.core.generate.main(args, conf)
    dd = conf['paths']['datadir']
    # Here results is a dict
    results = load_recent_results_in_datadir(1, dd, success_only=False)
    assert isinstance(results, dict)
    res_len = sum([len(results[fp]) for fp in results])
    assert res_len == 2, 'There should be two results in the datadir'
    # And here we change it to a list
    results = [r for fp in results for r in results[fp]]
    for result in results:
        assert isinstance(result, ResultSuccess), 'All existing results '\
            'should be a success'
    captured = capfd.readouterr()
    stdout_lines = captured.out.strip().split('\n')
    assert len(stdout_lines) == 1 + NUM_LINES_HEADER_V110

    speed = 7500
    rtt = round(median([round(r * 1000) for r in result.rtts]))
    bw_line = V3BWLine(result.fingerprint, speed, nick=result.nickname,
                       rtt=rtt,
                       master_key_ed25519=result.master_key_ed25519,
                       time=unixts_to_isodt_str(round(result.time)),
                       success=2, error_circ=0, error_misc=0,
                       error_stream=0)
    assert stdout_lines[NUM_LINES_HEADER_V110] + '\n' == str(bw_line)


def test_generate_two_relays_success_noscale(
        dotsbws_success_result_two_relays, parser, capfd):
    dotsbws = dotsbws_success_result_two_relays
    args = parser.parse_args(
        '-d {} --log-level DEBUG generate --output /dev/stdout'
        .format(dotsbws.name).split())
    conf = get_config(args)
    sbws.core.generate.main(args, conf)
    dd = conf['paths']['datadir']
    # Here results is a dict
    results = load_recent_results_in_datadir(1, dd, success_only=False)
    assert isinstance(results, dict)
    res_len = sum([len(results[fp]) for fp in results])
    assert res_len == 4, 'There should be 4 results in the datadir'
    # And here we change it to a list
    results = [r for fp in results for r in results[fp]]
    for result in results:
        assert isinstance(result, ResultSuccess), 'All existing results '\
            'should be a success'
    captured = capfd.readouterr()
    stdout_lines = captured.out.strip().split('\n')
    assert len(stdout_lines) == 2 + NUM_LINES_HEADER_V110

    r1_results = [r for r in results if r.fingerprint == 'A' * 40]
    r1_time = unixts_to_isodt_str(round(max([r.time for r in r1_results])))
    r1_name = r1_results[0].nickname
    r1_fingerprint = r1_results[0].fingerprint
    r1_ed25519 = r1_results[0].master_key_ed25519
    r1_speeds = [dl['amount'] / dl['duration'] / 1024
                 for r in r1_results for dl in r.downloads]
    r1_speed = round(median(r1_speeds))
    r1_rtt = round(median([round(rtt * 1000) for r in r1_results
                           for rtt in r.rtts]))
    bw_line = V3BWLine(r1_fingerprint, r1_speed, nick=r1_name, rtt=r1_rtt,
                       time=r1_time, master_key_ed25519=r1_ed25519,
                       success=2, error_circ=0, error_misc=0,
                       error_stream=0)
    # FIXME: left side does not contain ed25519
    # assert stdout_lines[1 + NUM_LINES_HEADER_V110] + '\n' == str(bw_line)
    r2_results = [r for r in results if r.fingerprint == 'B' * 40]
    r2_time = unixts_to_isodt_str(round(max([r.time for r in r2_results])))
    r2_name = r2_results[0].nickname
    r2_fingerprint = r2_results[0].fingerprint
    r2_ed25519 = r2_results[0].master_key_ed25519
    r2_speeds = [dl['amount'] / dl['duration'] / 1024
                 for r in r2_results for dl in r.downloads]
    r2_speed = round(median(r2_speeds))
    r2_rtt = round(median([round(rtt * 1000) for r in r2_results
                           for rtt in r.rtts]))
    bw_line = V3BWLine(r2_fingerprint, r2_speed, nick=r2_name, rtt=r2_rtt,
                       time=r2_time, master_key_ed25519=r2_ed25519,
                       success=2, error_circ=0, error_misc=0,
                       error_stream=0)
    assert stdout_lines[NUM_LINES_HEADER_V110] + '\n' == str(bw_line)
