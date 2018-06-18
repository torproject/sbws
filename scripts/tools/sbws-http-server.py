#!/usr/bin/env python3
# File: sbws-http-server.py
# Author: Matt Traudt
# License: CC0
#
# This script implements just enough of the HTTP protocol to work with Simple
# Bandwidth Scanner.
#
# All requested URLs exist. All return 1 GiB of garbage data. We always speak
# HTTP/1.1 because that's necessary for Keep-Alive request headers
# (used by sbws scanners) to work.
#
# HEAD and GET requests are supported to the minimum extent necessary.
# This essentially means that if the client sends Range request headers just
# like sbws does, then we'll only send back the number of bytes they requested.
# Indeed, this was the motivating reason for the complexity of this script;
# normally I would have used SimpleHTTPRequestHandler unmodified.
#
# Don't breathe too hard or this script might break.
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import http.server
from http import HTTPStatus
# import time

FILE_SIZE = 1*1024*1024*1024  # 1 GiB


def _get_resp_size_from_range(range_str):
    assert range_str.startswith('bytes=')
    range_str = range_str[len('bytes='):]
    start_byte, end_byte = range_str.split('-')
    return int(end_byte) - int(start_byte) + 1


class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    def send_head(self, length):
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Length', length)
        # self.send_header('Last-Modified', self.date_time_string(time.time()))
        self.end_headers()

    def do_GET(self):
        range_hdr = self.headers['Range']
        if not range_hdr:
            num_bytes = FILE_SIZE
        else:
            assert range_hdr.startswith('bytes=')
            num_bytes = _get_resp_size_from_range(range_hdr)
        self.send_head(num_bytes)
        self.wfile.write(b'A' * num_bytes)

    def do_HEAD(self):
        self.send_head(FILE_SIZE)


def main(args):
    addr = ('', args.port)
    print('Listening on', addr)
    httpd = http.server.HTTPServer(addr, MyHTTPRequestHandler)
    httpd.serve_forever()


if __name__ == '__main__':
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-p', '--port', default=8000, type=int, help='Port on which to listen')
    args = parser.parse_args()
    try:
        exit(main(args))
    except KeyboardInterrupt:
        pass
