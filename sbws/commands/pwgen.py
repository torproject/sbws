from argparse import ArgumentDefaultsHelpFormatter
import random

PW_LEN = 64
ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'


def gen_parser(sub):
    d = 'Generate a password suitable for use by a sbws client for '\
        'authenticating to an sbws server.'
    sub.add_parser('pwgen', formatter_class=ArgumentDefaultsHelpFormatter,
                   description=d)


def rand_char():
    return random.choice(ALPHABET)


def rand_str():
    s = ''
    while len(s) < PW_LEN:
        s += rand_char()
    return s


def main(args, conf, log_):
    global log
    log = log_
    s = rand_str()
    print(s)
