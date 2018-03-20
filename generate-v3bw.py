#!/usr/bin/env python3
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
import os
import json
import time
from statistics import median


def read_result_file(fname, starting_dict=None):
    data = starting_dict if starting_dict else {}
    with open(fname, 'rt') as fd:
        for line in fd:
            d = json.loads(line)
            fp = d['fingerprint']
            if fp not in data:
                data[fp] = []
            data[fp].append(d)
    return data


def result_data_to_v3bw_line(data, fingerprint):
    assert fingerprint in data
    results = data[fingerprint]
    nick = results[0]['nickname']
    speeds = [r['amount'] / r['duration'] for r in results]
    speed = median(speeds)
    frmt = 'node_id={fp} bw={sp} nick={n}'
    return frmt.format(fp=fingerprint, sp=round(speed), n=nick)


def main(args):
    assert os.path.isdir(args.result_directory)
    data_fnames = sorted(os.listdir(args.result_directory), reverse=True)
    data_fnames = data_fnames[0:14]
    data_fnames = [os.path.join(args.result_directory, f) for f in data_fnames]
    data = {}
    for fname in data_fnames:
        data = read_result_file(fname, data)
    with open(args.output, 'wt') as fd:
        fd.write('{}\n'.format(int(time.time())))
        for fp in data:
            fd.write('{}\n'.format(result_data_to_v3bw_line(data, fp)))


if __name__ == '__main__':
    parser = ArgumentParser(
            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--result-directory', default='dd', type=str,
                        help='Where result data from scanner.py is stored')
    parser.add_argument('--output', default='/dev/stdout', type=str,
                        help='Where to write v3bw file')
    args = parser.parse_args()
    main(args)
