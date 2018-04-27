from ..util.simpleauth import authenticate_scanner
from ..util.sockio import read_line
from sbws.globals import (fail_hard, is_initted)
from sbws.globals import MIN_REQ_BYTES, MAX_REQ_BYTES, SOCKET_TIMEOUT
from argparse import ArgumentDefaultsHelpFormatter
from functools import lru_cache
from threading import Thread
import socket
import time
import random
import os
import logging

log = logging.getLogger(__name__)


def gen_parser(sub):
    d = 'The server side of sbws. This should be run on the same machine as '\
        'a helper relay. This listens for scanners connections and responds '\
        'with the number of bytes the scanner requests.'
    sub.add_parser('server', formatter_class=ArgumentDefaultsHelpFormatter,
                   description=d)


def close_socket(s):
    try:
        log.info('Closing fd %d', s.fileno())
        s.shutdown(socket.SHUT_RDWR)
        s.close()
    except OSError:
        pass


def get_send_amount(sock):
    line = read_line(sock, max_len=16)
    if line is None:
        return None
    # if len(line) == 16, then it is much more likely we read garbage or not an
    # entire line instead of a legit number of bytes to send. So say we've
    # failed.
    if len(line) == 16:
        return None
    try:
        send_amount = int(line)
    except (TypeError, ValueError):
        return None
    return send_amount


@lru_cache(maxsize=8)
def _generate_random_string(length):
    ''' Generates a VERY WEAKLY random string. It felt wrong only sending a
    ton of a single character, but generating a long and "truely" random
    string is way too expensive. Furthermore, we don't just send random bytes
    (which may be easy to generate) because for some reason I have it in my
    head that doing everything in simple ascii, 1 byte == 1 char, and sometimes
    line-based way is a smart idea.

    Anyway. This shuffles the alphabet. It then concatenates this shuffled
    alphabet as many times as necessary to get a string as long or longer than
    the required length. It then returns the string up until the required
    length.

    Oh. Also it caches a few results based on the requested length. That's
    another thing that hurts its randomness.
    '''
    assert length > 0
    # start = time.time()
    repeats = int(length / len(_generate_random_string.alphabet)) + 1
    rng.shuffle(_generate_random_string.alphabet)
    s = ''.join(_generate_random_string.alphabet)
    s = s * repeats
    # stop = time.time()
    # _generate_random_string.acc += stop - start
    # if stop >= 60 + _generate_random_string.last_log:
    #     log.info('Spent', _generate_random_string.acc,
    #              'seconds in the last minute generating "random" strings')
    #     _generate_random_string.acc = 0
    #     _generate_random_string.last_log = stop
    assert len(s) >= length
    return s[:length]


_generate_random_string.alphabet = list('abcdefghijklmnopqrstuvwxyz'
                                        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                                        '0123456789')
# _generate_random_string.acc = 0
# _generate_random_string.last_log = time.time()


def write_to_scanner(sock, conf, amount):
    ''' Returns True if successful; else False '''
    log.debug('Sending scanner no. %d %d bytes', sock.fileno(), amount)
    while amount > 0:
        amount_this_time = min(conf.getint('server', 'max_send_per_write'),
                               amount)
        amount -= amount_this_time
        try:
            sock.send(bytes(
                _generate_random_string(amount_this_time), 'utf-8'))
        except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
            log.info('fd %d: %s', sock.fileno(), e)
            return False
    return True


def new_thread(args, conf, sock):
    def closure():
        scanner_name = authenticate_scanner(
            sock, conf['server.passwords'])
        if not scanner_name:
            log.info('Scanner did not provide valid auth')
            close_socket(sock)
            return
        log.info('%s authenticated on %d', scanner_name, sock.fileno())
        while True:
            send_amount = get_send_amount(sock)
            if send_amount is None:
                log.debug('Couldn\'t get an amount to send to %d',
                          sock.fileno())
                break
            if send_amount < MIN_REQ_BYTES or send_amount > MAX_REQ_BYTES:
                log.warning('%s requested %d bytes, which is not valid',
                            scanner_name, send_amount)
                break
            write_to_scanner(sock, conf, send_amount)
        log.info('%s on %d went away', scanner_name, sock.fileno())
        close_socket(sock)
    thread = Thread(target=closure)
    return thread


def main(args, conf):
    global rng
    rng = random.SystemRandom()
    if not is_initted(args.directory):
        fail_hard('Sbws isn\'t initialized. Try sbws init')

    if len(conf['server.passwords']) < 1:
        conf_fname = os.path.join(args.directory, 'config.ini')
        fail_hard('Sbws server needs at least one password in the section '
                  '[server.passwords] in the config file in %s. See '
                  'DEPLOY.rst for more information.', conf_fname)

    h = (conf['server']['bind_ip'], conf.getint('server', 'bind_port'))
    log.info('Binding to %s:%d', *h)
    while True:
        try:
            # first try IPv4
            log.debug('Trying to bind while assuming ipv4')
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(h)
        except OSError as e1:
            try:
                # then try IPv6
                log.debug('Trying to bind while assuming ipv6')
                server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                server.bind(h)
            except OSError as e2:
                log.warning('IPv4 bind error: %s', e1)
                log.warning('IPv6 bind error: %s', e2)
                time.sleep(5)
            else:
                break
        else:
            break
    log.info('Listening on %s:%d', h[0], h[1])
    server.listen(5)
    try:
        while True:
            sock, addr = server.accept()
            sock.settimeout(SOCKET_TIMEOUT)
            log.info('accepting connection from %s:%d as %d', addr[0], addr[1],
                     sock.fileno())
            t = new_thread(args, conf, sock)
            t.start()
    except KeyboardInterrupt:
        pass
    finally:
        log.info('Generate random string stats: %s',
                 _generate_random_string.cache_info())
        close_socket(server)
