from sbws import version
import sbws.core.generate
from sbws.util.config import get_config
from sbws.lib.resultdump import load_recent_results_in_datadir
from sbws.lib.resultdump import ResultSuccess
from statistics import median


def test_generate_no_dotsbws(tmpdir, parser, log):
    dotsbws = tmpdir
    args = parser.parse_args(
        '-d {} -vvvv generate'.format(dotsbws).split())
    conf = get_config(args, log.debug)
    try:
        sbws.core.generate.main(args, conf, log)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    lines = [l for l in log.test_get_logged_lines()]
    assert 'Sbws isn\'t initialized' in lines[-1]


def test_generate_no_datadir(empty_dotsbws, parser, log):
    dotsbws = empty_dotsbws
    args = parser.parse_args(
        '-d {} -vvvv generate'.format(dotsbws.name).split())
    conf = get_config(args, log.debug)
    try:
        sbws.core.generate.main(args, conf, log)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    lines = [l for l in log.test_get_logged_lines()]
    dd = conf['paths']['datadir']
    assert '{} does not exist'.format(dd) in lines[-1]


def test_generate_bad_scale_constant(empty_dotsbws_datadir, parser, log):
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} -vvvv generate --scale-constant -1'
        .format(dotsbws.name).split())
    conf = get_config(args, log.debug)
    try:
        sbws.core.generate.main(args, conf, log)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    log_lines = [l for l in log.test_get_logged_lines()]
    assert '--scale-constant must be positive' == log_lines[-1]


def test_generate_empty_datadir(empty_dotsbws_datadir, parser, log):
    dotsbws = empty_dotsbws_datadir
    args = parser.parse_args(
        '-d {} -vvvv generate'.format(dotsbws.name).split())
    conf = get_config(args, log.debug)
    sbws.core.generate.main(args, conf, log)
    log_lines = [l for l in log.test_get_logged_lines()]
    assert 'No recent results' in log_lines[-1]


def test_generate_single_error(dotsbws_error_result, parser, log):
    dotsbws = dotsbws_error_result
    args = parser.parse_args(
        '-d {} -vvvv generate'.format(dotsbws.name).split())
    conf = get_config(args, log.debug)
    sbws.core.generate.main(args, conf, log)
    log_lines = [l for l in log.test_get_logged_lines()]
    dd = conf['paths']['datadir']
    for line in log_lines:
        if 'Read 0 lines from {}'.format(dd) in line:
            break
    else:
        assert None, 'Unable to find log line indicating 0 success results '\
            'in data file'
    assert 'No recent results' in log_lines[-1]


def test_generate_single_success_noscale(dotsbws_success_result, parser, log,
                                         capfd):
    dotsbws = dotsbws_success_result
    args = parser.parse_args(
        '-d {} -vvvv generate'.format(dotsbws.name).split())
    conf = get_config(args, log.debug)
    sbws.core.generate.main(args, conf, log)
    dd = conf['paths']['datadir']
    results = load_recent_results_in_datadir(
        1, dd, success_only=False, log_fn=log.debug)
    assert len(results) == 1, 'There should be one result in the datadir'
    result = results[0]
    assert isinstance(result, ResultSuccess), 'The one existing result '\
        'should be a success'
    captured = capfd.readouterr()
    stdout_lines = captured.out.strip().split('\n')
    assert len(stdout_lines) == 3

    # XXX: after mocking time, make sure first line is the current timestamp
    # assert stdout_lines[0] is current timestamp

    v = 'version={}'.format(version)
    assert stdout_lines[1] == v

    bw = round(median([dl['amount'] / dl['duration']
                       for dl in result.downloads]))
    rtt = median([round(r * 1000) for r in result.rtts])
    bw_line = 'node_id={} bw={} nick={} rtt={} time={}'.format(
        result.fingerprint, bw, result.nickname, rtt, round(result.time))
    assert stdout_lines[2] == bw_line


def test_generate_single_success_scale(dotsbws_success_result, parser, log,
                                       capfd):
    dotsbws = dotsbws_success_result
    args = parser.parse_args(
        '-d {} -vvvv generate --scale'.format(dotsbws.name).split())
    conf = get_config(args, log.debug)
    sbws.core.generate.main(args, conf, log)
    dd = conf['paths']['datadir']
    results = load_recent_results_in_datadir(
        1, dd, success_only=False, log_fn=log.debug)
    assert len(results) == 1, 'There should be one result in the datadir'
    result = results[0]
    assert isinstance(result, ResultSuccess), 'The one existing result '\
        'should be a success'
    captured = capfd.readouterr()
    stdout_lines = captured.out.strip().split('\n')
    assert len(stdout_lines) == 3

    # XXX: after mocking time, make sure first line is the current timestamp
    # assert stdout_lines[0] is current timestamp

    v = 'version={}'.format(version)
    assert stdout_lines[1] == v

    bw = 7500
    rtt = median([round(r * 1000) for r in result.rtts])
    bw_line = 'node_id={} bw={} nick={} rtt={} time={}'.format(
        result.fingerprint, bw, result.nickname, rtt, round(result.time))
    assert stdout_lines[2] == bw_line


def test_generate_single_relay_success_noscale(
        dotsbws_success_result_one_relay, parser, log, capfd):
    dotsbws = dotsbws_success_result_one_relay
    args = parser.parse_args(
        '-d {} -vvvv generate'.format(dotsbws.name).split())
    conf = get_config(args, log.debug)
    sbws.core.generate.main(args, conf, log)
    dd = conf['paths']['datadir']
    results = load_recent_results_in_datadir(
        1, dd, success_only=False, log_fn=log.debug)
    assert len(results) == 2, 'There should be two results in the datadir'
    for result in results:
        assert isinstance(result, ResultSuccess), 'All existing results '\
            'should be a success'
    captured = capfd.readouterr()
    stdout_lines = captured.out.strip().split('\n')
    assert len(stdout_lines) == 3

    # XXX: after mocking time, make sure first line is the current timestamp
    # assert stdout_lines[0] is current timestamp

    v = 'version={}'.format(version)
    assert stdout_lines[1] == v

    speeds = [dl['amount'] / dl['duration'] for r in results
              for dl in r.downloads]
    speed = round(median(speeds))
    rtt = round(median([round(r * 1000) for r in result.rtts]))
    bw_line = 'node_id={} bw={} nick={} rtt={} time={}'.format(
        result.fingerprint, speed, result.nickname, rtt, round(result.time))
    assert stdout_lines[2] == bw_line


def test_generate_single_relay_success_scale(
        dotsbws_success_result_one_relay, parser, log, capfd):
    dotsbws = dotsbws_success_result_one_relay
    args = parser.parse_args(
        '-d {} -vvvv generate --scale'.format(dotsbws.name).split())
    conf = get_config(args, log.debug)
    sbws.core.generate.main(args, conf, log)
    dd = conf['paths']['datadir']
    results = load_recent_results_in_datadir(
        1, dd, success_only=False, log_fn=log.debug)
    assert len(results) == 2, 'There should be two results in the datadir'
    for result in results:
        assert isinstance(result, ResultSuccess), 'All existing results '\
            'should be a success'
    captured = capfd.readouterr()
    stdout_lines = captured.out.strip().split('\n')
    assert len(stdout_lines) == 3

    # XXX: after mocking time, make sure first line is the current timestamp
    # assert stdout_lines[0] is current timestamp

    v = 'version={}'.format(version)
    assert stdout_lines[1] == v

    speed = 7500
    rtt = round(median([round(r * 1000) for r in result.rtts]))
    bw_line = 'node_id={} bw={} nick={} rtt={} time={}'.format(
        result.fingerprint, speed, result.nickname, rtt, round(result.time))
    assert stdout_lines[2] == bw_line


def test_generate_two_relays_success_noscale(
        dotsbws_success_result_two_relays, parser, log, capfd):
    dotsbws = dotsbws_success_result_two_relays
    args = parser.parse_args(
        '-d {} -vvvv generate'.format(dotsbws.name).split())
    conf = get_config(args, log.debug)
    sbws.core.generate.main(args, conf, log)
    dd = conf['paths']['datadir']
    results = load_recent_results_in_datadir(
        1, dd, success_only=False, log_fn=log.debug)
    assert len(results) == 4, 'There should be 4 results in the datadir'
    for result in results:
        assert isinstance(result, ResultSuccess), 'All existing results '\
            'should be a success'
    captured = capfd.readouterr()
    stdout_lines = captured.out.strip().split('\n')
    assert len(stdout_lines) == 4

    # XXX: after mocking time, make sure first line is the current timestamp
    # assert stdout_lines[0] is current timestamp

    v = 'version={}'.format(version)
    assert stdout_lines[1] == v

    r1_results = [r for r in results if r.fingerprint == 'A' * 40]
    r1_time = round(max([r.time for r in r1_results]))
    r1_name = r1_results[0].nickname
    r1_fingerprint = r1_results[0].fingerprint
    r1_speeds = [dl['amount'] / dl['duration'] for r in r1_results
                 for dl in r.downloads]
    r1_speed = round(median(r1_speeds))
    r1_rtt = round(median([round(rtt * 1000) for r in r1_results
                           for rtt in r.rtts]))
    bw_line = 'node_id={} bw={} nick={} rtt={} time={}'.format(
        r1_fingerprint, r1_speed, r1_name, r1_rtt, r1_time)
    assert stdout_lines[3] == bw_line

    r2_results = [r for r in results if r.fingerprint == 'B' * 40]
    r2_time = round(max([r.time for r in r2_results]))
    r2_name = r2_results[0].nickname
    r2_fingerprint = r2_results[0].fingerprint
    r2_speeds = [dl['amount'] / dl['duration'] for r in r2_results
                 for dl in r.downloads]
    r2_speed = round(median(r2_speeds))
    r2_rtt = round(median([round(rtt * 1000) for r in r2_results
                           for rtt in r.rtts]))
    bw_line = 'node_id={} bw={} nick={} rtt={} time={}'.format(
        r2_fingerprint, r2_speed, r2_name, r2_rtt, r2_time)
    assert stdout_lines[2] == bw_line
