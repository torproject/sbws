from sbws.globals import (fail_hard, is_initted)
from sbws.lib.resultdump import Result
from sbws.lib.resultdump import ResultError
from sbws.lib.resultdump import ResultSuccess
from sbws.lib.resultdump import load_recent_results_in_datadir
from sbws.lib.resultdump import group_results_by_relay
from argparse import ArgumentDefaultsHelpFormatter
import os
from datetime import date
from datetime import timedelta
from statistics import mean


def _print_stats_error_types(data):
    counts = {'total': 0}
    for fp in data:
        results = data[fp]
        for result in results:
            if result.type not in counts:
                log.debug('Found a', result.type, 'for the first time')
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
            number, counts['total'], 100*number/counts['total'], count_type))


def _print_averages(data):
    mean_success = mean([
        len([r for r in data[fp] if isinstance(r, ResultSuccess)])
        for fp in data])
    print('Average {:.2f} successful measurements per '
          'relay'.format(mean_success))


def print_stats(args, data):
    '''
    Called from main to print various statistics about the organized **data**
    to stdout.

    :param argparse.Namespace args: command line arguments
    :param dict data: keyed by relay fingerprint, and with values of
        :class:`sbws.lib.resultdump.Result` subclasses
    '''
    results = []
    for fp in data:
        results.extend(data[fp])
    assert len([r for r in results if not isinstance(r, Result)]) == 0
    error_results = [r for r in results if isinstance(r, ResultError)]
    success_results = [r for r in results if isinstance(r, ResultSuccess)]
    percent_success_results = 100 * len(success_results) / len(results)
    first_time = min([r.time for r in results])
    last_time = max([r.time for r in results])
    first = date.fromtimestamp(first_time)
    last = date.fromtimestamp(last_time)
    duration = timedelta(seconds=last_time-first_time)
    # remove microseconds for prettier printing
    duration = duration - timedelta(microseconds=duration.microseconds)
    print(len(data), 'relays have recent results')
    _print_averages(data)
    print(len(results), 'total results, and {:.1f}% are successes'.format(
        percent_success_results))
    print(len(success_results), 'success results and',
          len(error_results), 'error results')
    print('Results come from', first, 'to', last, 'over a period of',
          duration)
    if args.error_types:
        _print_stats_error_types(data)


def gen_parser(sub):
    '''
    Helper function for the broader argument parser generating code that adds
    in all the possible command line arguments for the stats command.

    :param argparse._SubParsersAction sub: what to add a sub-parser to
    '''
    d = 'Write some statistics about the data collected so far to stdout'
    p = sub.add_parser('stats', formatter_class=ArgumentDefaultsHelpFormatter,
                       description=d)
    p.add_argument('--error-types', action='store_true',
                   help='Also print information about each error type')


def main(args, conf, log_):
    '''
    Main entry point into the stats command.

    :param argparse.Namespace args: command line arguments
    :param configparser.ConfigParser conf: parsed config files
    :param sbws.lib.pastlylogger.PastlyLogger log_: logging class instance
    '''
    global log
    log = log_
    if not is_initted(args.directory):
        fail_hard('Sbws isn\'t initialized. Try sbws init', log=log)

    datadir = conf['paths']['datadir']
    if not os.path.isdir(datadir):
        fail_hard(datadir, 'does not exist', log=log)

    fresh_days = conf.getint('general', 'data_period')
    results = load_recent_results_in_datadir(
        fresh_days, datadir, success_only=False, log_fn=log.debug)
    if len(results) < 1:
        log.notice('No fresh results')
        return
    data = group_results_by_relay(results)
    print_stats(args, data)
