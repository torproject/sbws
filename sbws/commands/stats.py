from sbws.globals import (fail_hard, is_initted)
from sbws.lib.resultdump import Result
from sbws.lib.resultdump import ResultError
from sbws.lib.resultdump import ResultSuccess
from argparse import ArgumentDefaultsHelpFormatter
import os
import json
from datetime import date
from datetime import timedelta


def read_result_file(fname, starting_dict=None):
    data = starting_dict if starting_dict else {}
    with open(fname, 'rt') as fd:
        for line in fd:
            d = json.loads(line)
            res = Result.from_dict(d)
            fp = d['fingerprint']
            if fp not in data:
                data[fp] = []
            data[fp].append(res)
    return data


def print_stats(data):
    results = []
    for fp in data:
        results.extend(data[fp])
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
    print(len(results), 'total results, and {:.1f}% are successes'.format(
        percent_success_results))
    print(len(success_results), 'success results and',
          len(error_results), 'error results')
    print('Results come from', first, 'to', last, 'over a period of',
          duration)


def gen_parser(sub):
    p = sub.add_parser('stats',
                       formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('--result-directory', default='dd', type=str,
                   help='Where result data from the sbws client is stored')


def main(args, log_):
    global log
    log = log_
    if not is_initted(os.getcwd()):
        fail_hard('Directory isn\'t initted')
    if not os.path.isdir(args.result_directory):
        fail_hard(args.result_directory, 'does not exist')

    data_fnames = sorted(os.listdir(args.result_directory), reverse=True)
    data_fnames = data_fnames[0:14]
    data_fnames = [os.path.join(args.result_directory, f) for f in data_fnames]
    data = {}
    for fname in data_fnames:
        data = read_result_file(fname, data)
    print_stats(data)
