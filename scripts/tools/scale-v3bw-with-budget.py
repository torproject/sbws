#!/usr/bin/env python3
# File: scale-v3bw-with-budget.py
# Written by: Matt Traudt
# Copyright/License: CC0
from collections import OrderedDict
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType
import sys


def fail_hard(*s):
    print(*s, file=sys.stderr)
    exit(1)


def line_into_dict(line):
    words = line.strip().split()
    d = OrderedDict()
    for word in words:
        key, value = word.split('=')
        d.update({key: value})
    return d


def main(args):
    total_input_weight = 0
    line_dicts = []
    is_first_line = True
    for line in args.input:
        if is_first_line:
            # First line is special and is supposed to be a timestamp
            try:
                int(line)
            except ValueError as e:
                fail_hard('First line should be an int.', e)
            is_first_line = False
            args.output.write(line)
            continue
        # All lines but the first go through this
        d = line_into_dict(line)
        # Check that the required parts of the line are here
        if 'node_id' not in d:
            fail_hard('Line without required node_id:', line)
        if 'bw' not in d:
            fail_hard('Line without required bw:', line)
        # Make sure the bw looks like an int
        try:
            d['bw'] = int(d['bw'])
        except ValueError as e:
            fail_hard('Found a non-int bw value', d['bw'], e)
        # Accumulate the total "bandwidth" weights on the input side
        total_input_weight += d['bw']
        # And keep the line for later
        line_dicts.append(d)
    # Now calculate a ratio to multiply every line by. It's the total budget we
    # should give ourselves based on the number of relays in the v3bw file (AKA
    # the total output weight) divided by the total input weight
    ratio = (len(line_dicts) * args.budget_per_relay) / total_input_weight
    for d in line_dicts:
        d['bw'] = round(d['bw'] * ratio)
        # Accumulate all the parts of the line back together
        s = ''
        for key in d:
            s += '{}={} '.format(key, d[key])
        # Remove trailing ' ' and replace with '\n'
        s = s.rstrip() + '\n'
        args.output.write(s)


def gen_parser():
    d = 'Read a v3bw file, adjust the bandwidth weights of the relays, and '\
        'write the new v3bw file out. For each relay in the v3bw file, we '\
        'give ourselves some amount of weight to work with. We then '\
        'distribute this weight to the relays in the same proportions their '\
        'input weights were in. This cases the scale of theie weights to '\
        'move up or down, but their relative weights stay the same.'
    p = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter,
                       description=d)
    p.add_argument('-i', '--input', type=FileType('rt'),
                   default='/dev/stdin',
                   help='Input v3bw file to be scaled')
    p.add_argument('-o', '--output', type=FileType('wt'),
                   default='/dev/stdout',
                   help='Where to write a new, and scaled, v3bw file')
    p.add_argument('--budget-per-relay', type=float, default=7500,
                   help='Per relay in the v3bw file, add this much to our '
                   'budget')
    return p


if __name__ == '__main__':
    p = gen_parser()
    args = p.parse_args()
    exit(main(args))
