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


class V3BWLine:
    def __init__(self, fp, bw, nick, rtts):
        self.fp = fp
        self.bw = bw
        self.nick = nick
        # convert to ms
        rtts = [round(r * 1000) for r in rtts]
        self.rtt = round(median(rtts))

    def __str__(self):
        frmt = 'node_id={fp} bw={sp} nick={n} rtt={rtt}'
        return frmt.format(fp=self.fp, sp=round(self.bw), n=self.nick,
                           rtt=self.rtt)


def result_data_to_v3bw_line(data, fingerprint):
    assert fingerprint in data
    results = data[fingerprint]
    nick = results[0]['nickname']
    speeds = [dl['amount'] / dl['duration']
              for r in results for dl in r['downloads']]
    speed = median(speeds)
    rtts = [rtt for r in results for rtt in r['rtts']]
    return V3BWLine(fingerprint, speed, nick, rtts)


def scale_lines(v3bw_lines, scale_max):
    total = sum([l.bw for l in v3bw_lines])
    ratio = scale_max / total
    for line in v3bw_lines:
        line.bw = round(line.bw * ratio)
    return v3bw_lines


def main(args):
    assert os.path.isdir(args.result_directory)
    data_fnames = sorted(os.listdir(args.result_directory), reverse=True)
    data_fnames = data_fnames[0:14]
    data_fnames = [os.path.join(args.result_directory, f) for f in data_fnames]
    data = {}
    for fname in data_fnames:
        data = read_result_file(fname, data)
    data_lines = [result_data_to_v3bw_line(data, fp) for fp in data]
    data_lines = sorted(data_lines, key=lambda d: d.bw, reverse=True)
    data_lines = scale_lines(data_lines, args.scale_max)
    with open(args.output, 'wt') as fd:
        fd.write('{}\n'.format(int(time.time())))
        for line in data_lines:
            fd.write('{}\n'.format(str(line)))


if __name__ == '__main__':
    parser = ArgumentParser(
            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--result-directory', default='dd', type=str,
                        help='Where result data from scanner.py is stored')
    parser.add_argument('--output', default='/dev/stdout', type=str,
                        help='Where to write v3bw file')
    parser.add_argument('--scale-max', default=50000000, type=int,
                        help='When scaling bw weights, scale them up/down '
                        'as if this is the sum of all measurements')
    args = parser.parse_args()
    main(args)
