#!/usr/bin/env python3
import sys
import re
# File: v3bw-into-xy.py
# Author: Matt Traudt
# License: CC0
#
# Takes one or more v3bw files as arguments.
#
# Looks for lines that contain actual data. That means most of them, since most
# of them contain "node_id=" and those are the ones that are interesting.
#
# Extract the fingerprint and bandwidth values for each of those lines and put
# them on stdout, one per line. Effectively, after ignoring other lines, this:
#     node_id=$AAAA...AAAA bw=12345
# becomes this:
#     AAAA...AAAA 12345
#
# NOTE: If you specify more than v3bw file, this will do NOTHING to tell you
# when the output from one file stops and the next begins
#
# With v1.1.0 of the v3bw file format, we no longer know if node_id or bw is
# first in the line. Hence two regular expresions and searching for the matched
# item that has 40 chars (the fingerprint)


def main():
    re1 = re.compile('.*node_id=\$?([\w]+).* bw=([\d]+).*')  # noqa
    re2 = re.compile('.*bw=([\d]+).* node_id=\$?([\w]+)')  # noqa
    for fname in sys.argv[1:]:
        with open(fname, 'rt') as fd:
            for line in fd:
                if 'node_id' not in line:
                    continue
                match = re1.match(line) or re2.match(line)
                if not match:
                    continue
                items = match.groups()
                assert len(items) == 2
                s = '{} {}\n'
                if len(items[0]) == 40:
                    s = s.format(*items)
                else:
                    s = s.format(*items[::-1])
                sys.stdout.write(s)
    return 0


if __name__ == '__main__':
    try:
        exit(main())
    except (KeyboardInterrupt, BrokenPipeError):
        pass
