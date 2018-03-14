#!/usr/bin/env python3
import sys
import socket
from threading import Thread

send_amount = None

def new_thread(sock):
    def closure():
        try:
            sock.send(b'a' * send_amount)
        except BrokenPipeError:
            pass
        try:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except:
            pass
    thread = Thread(target=closure)
    return thread

def main():
    global send_amount
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    h = (sys.argv[1], int(sys.argv[2]))
    send_amount = int(sys.argv[3])
    print('listening on', h)
    server.bind(h)
    server.listen(5)
    try:
        while True:
            sock, addr = server.accept()
            print('accepting connection from', addr)
            t = new_thread(sock)
            t.run()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()


def usage():
    print(sys.argv[0], 'bind-ip bind-port send-amount')


if __name__ == '__main__':
    if len(sys.argv) < 4:
        usage()
        exit(1)
    main()

