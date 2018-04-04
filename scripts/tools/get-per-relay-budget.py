#!/usr/bin/env python3
# File: get-per-relay-budget.py
# Written by: Matt Traudt
# Copyright/License: CC0
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from statistics import median
from statistics import mean
from stem.control import Controller
import stem


def _get_controller_port(args):
    return Controller.from_port(port=args.ctrl_port)


def _get_controller_socket(args):
    return Controller.from_socket_file(path=args.ctrl_socket)


def get_controller(args):
    try:
        cont = _get_controller_port(args)
    except stem.SocketError:
        cont = _get_controller_socket(args)
    return cont


def print_quiet(bws):
    print(round(mean(bws)))


def print_regular(bws):
    print(len(bws), 'relays')
    print('mean:', round(mean(bws)))
    print('median:', round(median(bws)))


def main(args):
    cont = get_controller(args)
    cont.authenticate()
    bws = []
    bws = [ns.bandwidth for ns in cont.get_network_statuses()]
    if args.quiet:
        print_quiet(bws)
    else:
        print_regular(bws)


def gen_parser():
    d = 'Get the consensus weight for every relay in the current consensus '\
        'and print some information about them.'
    p = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter,
                       description=d)
    p.add_argument('--ctrl-port', metavar='PORT', type=int, default=9051,
                   help='Port on which to control the Tor client')
    p.add_argument('--ctrl-socket', metavar='SOCK', type=str,
                   default='/var/run/tor/control',
                   help='Path to socket on which to control the Tor client')
    p.add_argument('-q', '--quiet', action='store_true',
                   help='If given, only print the mean bandwidth to stdout')
    return p


if __name__ == '__main__':
    p = gen_parser()
    args = p.parse_args()
    exit(main(args))
