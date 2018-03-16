#!/usr/bin/env python3
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
import sys
import socket
from threading import Thread

def new_thread(sock, send_amount):
    def closure():
        try:
            sock.send(b'a' * send_amount)
        except BrokenPipeError as e:
            print('fd', sock.fileno(), ':', e)
            pass
        try:
            print('Closing fd', sock.fileno())
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except Exception as e:
            print('fd', sock.fileno(), ':', e)
            pass
    thread = Thread(target=closure)
    return thread

def main(args):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    h = (args.bind_ip, args.bind_port)
    print('listening on', h)
    server.bind(h)
    server.listen(5)
    try:
        while True:
            sock, addr = server.accept()
            print('accepting connection from', addr)
            t = new_thread(sock, args.send_amount)
            t.run()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            sock.shutdown(socket.SHUT_RDWR)
            server.close()
        except Exception as e:
            print(e)
            pass


if __name__ == '__main__':
    parser = ArgumentParser(
            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('bind_ip', type=str, default='127.0.0.1')
    parser.add_argument('bind_port', type=int, default=4444)
    parser.add_argument('send_amount', type=int,
                        default=10*1024*1024)  # 10 MiB
    args = parser.parse_args()
    main(args)

