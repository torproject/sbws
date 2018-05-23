from sbws.globals import (fail_hard, is_initted)
from sbws.lib.v3bwfile import V3BwHeader
from sbws.lib.resultdump import ResultSuccess
from sbws.lib.resultdump import load_recent_results_in_datadir
from sbws.util.filelock import FileLock
from sbws.util.timestamp import unixts_to_isodt_str, unixts_to_str
from argparse import ArgumentDefaultsHelpFormatter
from statistics import median
import os
import logging

log = logging.getLogger(__name__)


# FIXME: move this to v3bwfile?
class V3BWLine:
    # TODO: docstrings
    def __init__(self, fp, bw, nick, rtts, last_time):
        # TODO: asserts checking arg types
        self.fp = fp
        self.nick = nick
        # convert to KiB and make sure the answer is at least 1
        self.bw = max(round(bw / 1024), 1)
        # convert to ms
        rtts = [round(r * 1000) for r in rtts]
        self.rtt = round(median(rtts))
        self.time = unixts_to_isodt_str(last_time)

    def __str__(self):
        frmt = 'node_id=${fp} bw={sp} nick={n} rtt={rtt} time={t}'
        return frmt.format(fp=self.fp, sp=self.bw, n=self.nick, rtt=self.rtt,
                           t=self.time)


def result_data_to_v3bw_line(data, fingerprint):
    assert fingerprint in data
    results = data[fingerprint]
    for res in results:
        assert isinstance(res, ResultSuccess)
    results = data[fingerprint]
    nick = results[0].nickname
    speeds = [dl['amount'] / dl['duration']
              for r in results for dl in r.downloads]
    speed = median(speeds)
    rtts = [rtt for r in results for rtt in r.rtts]
    last_time = round(max([r.time for r in results]))
    return V3BWLine(fingerprint, speed, nick, rtts, last_time)


def warn_if_not_accurate_enough(lines, constant):
    margin = 0.001
    accuracy_ratio = (sum([l.bw for l in lines]) / len(lines)) / constant
    log.info('The generated lines are within {:.5}% of what they should '
             'be'.format((1-accuracy_ratio)*100))
    if accuracy_ratio < 1 - margin or accuracy_ratio > 1 + margin:
        log.warning('There was %f%% error and only +/- %f%% is '
                    'allowed', (1-accuracy_ratio)*100, margin*100)


def scale_lines(args, v3bw_lines):
    assert len(v3bw_lines) > 0
    total = sum([l.bw for l in v3bw_lines])
    # In case total is zero, it will run on ZeroDivision
    assert total > 0
    if args.scale:
        scale = len(v3bw_lines) * args.scale_constant
    else:
        scale = total
    ratio = scale / total
    for line in v3bw_lines:
        line.bw = round(line.bw * ratio)
    if args.scale:
        warn_if_not_accurate_enough(v3bw_lines, args.scale_constant)
    return v3bw_lines


def gen_parser(sub):
    d = 'Generate a v3bw file based on recent results. A v3bw file is the '\
        'file Tor directory authorities want to read and base their '\
        'bandwidth votes on.'
    p = sub.add_parser('generate', description=d,
                       formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('--output', default=None, type=str,
                   help='If specified, write the v3bw here instead of what is'
                   'specified in the configuration')
    # The reason for --scale-constant defaulting to 7500 is because at one
    # time, torflow happened to generate output that averaged to 7500 bw units
    # per relay. We wanted the ability to try to be like torflow. See
    # https://lists.torproject.org/pipermail/tor-dev/2018-March/013049.html
    p.add_argument('--scale-constant', default=7500, type=int,
                   help='When scaling bw weights, scale them using this const '
                   'multiplied by the number of measured relays')
    p.add_argument('--scale', action='store_true',
                   help='If specified, do not use bandwidth values as they '
                   'are, but scale them such that we have a budget of '
                   'scale_constant * num_measured_relays = bandwidth to give '
                   'out, and we do so proportionally')


def log_stats(data_lines):
    assert len(data_lines) > 0
    total_bw = sum([l.bw for l in data_lines])
    bw_per_line = total_bw / len(data_lines)
    log.info('Mean bandwidth per line: %f "KiB"', bw_per_line)


def read_started_ts(conf):
    """Read ISO formated timestamp which represents the date and time
    when scanner started.

    :param ConfigParser conf: configuration
    :returns: str, ISO formated timestamp
    """
    filepath = conf['paths']['started_filepath']
    try:
        with FileLock(filepath):
            with open(filepath, 'r') as fd:
                generator_started = fd.read()
    except FileNotFoundError as e:
        log.warn('File %s not found.%s', filepath, e)
        return ''
    return generator_started


def main(args, conf):
    if not is_initted(args.directory):
        fail_hard('Sbws isn\'t initialized.  Try sbws init')

    datadir = conf['paths']['datadir']
    if not os.path.isdir(datadir):
        fail_hard('%s does not exist', datadir)
    if args.scale_constant < 1:
        fail_hard('--scale-constant must be positive')

    fresh_days = conf.getint('general', 'data_period')
    results = load_recent_results_in_datadir(
        fresh_days, datadir, success_only=True)
    if results:
        # Using naive datetime object without timezone, assumed utc
        timestamp = datetime.utcfromtimestamp(max([r.time for fp in results
                                                   for r in results[fp]]))
        lastest_bandwidth = timestamp.replace(microsecond=0).isoformat()
        earliest_bandwidth = datetime.utcfromtimestamp(
                                min([r.time for fp in results
                                     for r in results[fp]])) \
            .replace(microsecond=0).isoformat()
    if len(results) < 1:
        log.warning('No recent results, so not generating anything. (Have you '
                    'ran sbws scanner recently?)')
        return
    data_lines = [result_data_to_v3bw_line(results, fp) for fp in results]
    data_lines = sorted(data_lines, key=lambda d: d.bw, reverse=True)
    data_lines = scale_lines(args, data_lines)
    generator_started = read_started_ts(conf)
    if results:
        header = V3BwHeader(timestamp=timestamp,
                            lastest_bandwidth=lastest_bandwidth,
                            earliest_bandwidth=earliest_bandwidth,
                            generator_started=generator_started)
    else:
        header = V3BwHeader(generator_started=generator_started)
    log_stats(data_lines)
    output = conf['paths']['v3bw_fname']
    if args.output:
        output = args.output
    log.info('Writing v3bw file to %s', output)
    with open(output, 'wt') as fd:
        fd.write(str(header))
        for line in data_lines:
            fd.write('{}\n'.format(str(line)))
