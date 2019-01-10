import logging
import os
from argparse import ArgumentDefaultsHelpFormatter
from datetime import datetime, timedelta
from statistics import mean

from sbws.globals import fail_hard
from sbws.lib.resultdump import (Result, ResultError, ResultErrorCircuit,
                                 ResultErrorStream, ResultSuccess,
                                 load_recent_results_in_datadir)

log = logging.getLogger(__name__)


def _print_stats_error_types(data):
    counts = {'total': 0}
    for fp in data:
        results = data[fp]
        for result in results:
            if result.type not in counts:
                log.debug('Found a %s for the first time', result.type)
                counts[result.type] = 0
            counts[result.type] += 1
            counts['total'] += 1
    for count_type in counts:
        if count_type == 'total':
            continue
        if 'error' not in count_type:
            continue
        number = counts[count_type]
        print('{}/{} ({:.2f}%) results were {}'.format(
            number, counts['total'], 100 * number / counts['total'],
            count_type))


def _result_type_per_relay(data, result_type):
    out = {}
    for fp in data:
        out[fp] = len([r for r in data[fp] if isinstance(r, result_type)])
    return out


def _get_box_plot_values(iterable):
    """Reutrn the min, q1, med, q1, and max of the input list or iterable.
    This function is NOT perfect, and I think that's fine for basic statistical
    needs. Instead of median, it will return low or high median. Same for q1
    and q3. """
    if not isinstance(iterable, list):
        iterable = list(iterable)
    iterable.sort()
    length = len(iterable)
    median_idx = round(length / 2)
    q1_idx = round(length / 4)
    q3_idx = median_idx + q1_idx
    return [iterable[0], iterable[q1_idx], iterable[median_idx],
            iterable[q3_idx], iterable[length - 1]]


def _print_results_type_box_plot(data, result_type):
    per_relay = _result_type_per_relay(data, result_type)
    bp = _get_box_plot_values(per_relay.values())
    print('For {}: min={} q1={} med={} q3={} max={}'.format(
        result_type.__name__, *bp))


def _print_averages(data):
    mean_success = mean([
        len([r for r in data[fp] if isinstance(r, ResultSuccess)])
        for fp in data])
    print('Mean {:.2f} successful measurements per '
          'relay'.format(mean_success))
    _print_results_type_box_plot(data, Result)
    _print_results_type_box_plot(data, ResultSuccess)
    _print_results_type_box_plot(data, ResultErrorCircuit)
    _print_results_type_box_plot(data, ResultErrorStream)


def _results_into_bandwidths(results, limit=5):
    """
    For all the given resutls, extract their download statistics and normalize
    them into bytes/second bandwidths.

    :param list results: list of :class:`sbws.list.resultdump.ResultSuccess`
    :param int limit: The maximum number of bandwidths to return
    :returns: list of up to `limit` bandwidths, with the largest first
    """
    downloads = []
    for result in results:
        assert isinstance(result, ResultSuccess)
        for dl in result.downloads:
            downloads.append(dl['amount'] / dl['duration'])
    return sorted(downloads, reverse=True)[:limit]


def print_stats(args, data):
    """
    Called from main to print various statistics about the organized **data**
    to stdout.

    :param argparse.Namespace args: command line arguments
    :param dict data: keyed by relay fingerprint, and with values of
        :class:`sbws.lib.resultdump.Result` subclasses
    """
    results = []
    for fp in data:
        results.extend(data[fp])
    assert len([r for r in results if not isinstance(r, Result)]) == 0
    error_results = [r for r in results if isinstance(r, ResultError)]
    success_results = [r for r in results if isinstance(r, ResultSuccess)]
    percent_success_results = 100 * len(success_results) / len(results)
    fastest_transfers = _results_into_bandwidths(success_results)
    fastest_transfer = 0 if len(fastest_transfers) < 1 else \
        fastest_transfers[0]
    first_time = min([r.time for r in results])
    last_time = max([r.time for r in results])
    first = datetime.utcfromtimestamp(first_time)
    first = first - timedelta(microseconds=first.microsecond)
    last = datetime.utcfromtimestamp(last_time)
    last = last - timedelta(microseconds=last.microsecond)
    duration = last - first
    print(len(data), 'relays have recent results')
    _print_averages(data)
    print(len(results), 'total results, and {:.1f}% are successes'.format(
        percent_success_results))
    print(len(success_results), 'success results and',
          len(error_results), 'error results')
    print('The fastest download was {:.2f} KiB/s'.format(
        fastest_transfer / 1024))
    print('Results come from', first, 'to', last, 'over a period of',
          duration)
    if getattr(args, 'error_types', False) is True:
        _print_stats_error_types(data)


def gen_parser(sub):
    """
    Helper function for the broader argument parser generating code that adds
    in all the possible command line arguments for the stats command.

    :param argparse._SubParsersAction sub: what to add a sub-parser to
    """
    d = 'Write some statistics about the data collected so far to stdout'
    p = sub.add_parser('stats', formatter_class=ArgumentDefaultsHelpFormatter,
                       description=d)
    p.add_argument('--error-types', action='store_true',
                   help='Also print information about each error type')


def main(args, conf):
    """
    Main entry point into the stats command.

    :param argparse.Namespace args: command line arguments
    :param configparser.ConfigParser conf: parsed config files
    """

    datadir = conf.getpath('paths', 'datadir')
    if not os.path.isdir(datadir):
        fail_hard('%s does not exist', datadir)

    fresh_days = conf.getint('general', 'data_period')
    results = load_recent_results_in_datadir(
        fresh_days, datadir, success_only=False)
    if len(results) < 1:
        log.warning('No fresh results')
        return
    print_stats(args, results)
