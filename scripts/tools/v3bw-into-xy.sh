#!/usr/bin/env bash
# File: v3bw-into-xy.sh
# Author: Matt Traudt
# License: CC0
#
# Takes one or more v3bw files as arguments.
#
# Looks for lines that contain actual data. That means most of them, since most
# of them start with "node_id=" and those are the ones that are interesting.
#
# Extract the fingerprint and bandwidth values for each of those lines and put
# them on stdout, one per line. Effectively, after ignoring other lines, this:
#     node_id=$AAAA...AAAA bw=12345
# becomes this:
#     AAAA...AAAA 12345
#
# NOTE: If you specify more than v3bw file, this will do NOTHING to tell you
# when the output from one file stops and the next begins
set -e
while [ "$1" != "" ]
do
    grep '^node_id=' "$1" |
	    sed -r 's|^node_id=([$A-Z0-9]+) bw=([0-9]+).*$|\1 \2|' |
	    sed 's|\$||g'
    shift
done
