#!/usr/bin/env python3
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
import sys
import socket
import time
from threading import Thread

MAX_SEND_PER_WRITE = 100*1024*1024
MAX_SEND_PER_WRITE = 4096


def read_line(s):
    ''' read until b'\n' is seen on the socket <s>. Return everything up until
    the newline as a str. If nothing can be read, return None. Note how that is
    different than if a newline is the first character; in that case, an empty
    str is returned '''
    chars = None
    while True:
        try:
            c = s.recv(1)
        except ConnectionResetError as e:
            print(e)
            return None
        if not c:
            return chars
        if chars is None:
            chars = ''
        if c == b'\n':
            break
        chars += c.decode('utf-8')
    return chars


def close_socket(s):
    try:
        print('Closing fd', s.fileno())
        s.shutdown(socket.SHUT_RDWR)
        s.close()
    except OSError:
        pass


def get_send_amount(sock):
    l = read_line(sock)
    try:
        send_amount = int(l)
    except (TypeError, ValueError):
        return None
    return send_amount


def write_to_client(sock, amount):
    ''' Returns True if successful; else False '''
    print('Sending client no.', sock.fileno(), amount, 'bytes')
    while amount > 0:
        amount_this_time = min(MAX_SEND_PER_WRITE, amount)
        amount -= amount_this_time
        try:
            sock.send(b'a' * amount_this_time)
        except (ConnectionResetError, BrokenPipeError) as e:
            print('fd', sock.fileno(), ':', e)
            return False
    return True


def new_thread(sock):
    def closure():
        while True:
            send_amount = get_send_amount(sock)
            if send_amount is None:
                print('Couldn\'t get an amount to send to', sock.fileno())
                close_socket(sock)
                return
            write_to_client(sock, send_amount)
        close_socket(sock)
    thread = Thread(target=closure)
    return thread

def main(args):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    h = (args.bind_ip, args.bind_port)
    print('binding to', h)
    while True:
        try: server.bind(h)
        except OSError as e:
            print(e)
            time.sleep(5)
        else: break
    print('listening on', h)
    server.listen(5)
    try:
        while True:
            sock, addr = server.accept()
            print('accepting connection from', addr, 'as', sock.fileno())
            t = new_thread(sock)
            t.run()
    except KeyboardInterrupt:
        pass
    finally:
        close_socket(server)


if __name__ == '__main__':
    parser = ArgumentParser(
            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('bind_ip', type=str, default='127.0.0.1')
    parser.add_argument('bind_port', type=int, default=4444)
    args = parser.parse_args()
    main(args)

