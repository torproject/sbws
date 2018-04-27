import os
SBWS_VERSION = '0.1.0'
RESULT_VERSION = 1
WIRE_VERSION = 1
SPEC_VERSION = '1.1.0'

PKG_DIR = os.path.abspath(os.path.dirname(__file__))

SOCKET_TIMEOUT = 60  # seconds

# Minimum and maximum number of bytes a scanner is allowed to request from a
# server. If these are changed, a WIRE_VERSION bump is required, which also
# happens to require an sbws major version bump.
#
# Note for smart people and people who pull out Wireshark: Even if the scanner
# requests 1 byte, that request and the 1 byte response will each be carried
# over the Internet in 514 byte Tor cells. Theoretically we could bump the
# minimum request size up to ~498 bytes, but I see no reason why we should.
# Trying to hit the maximum cell size just makes sbws server send more, us read
# more, and it runs the risk of standards changing underneath us and sbws
# suddenly creating more than one cell.
MIN_REQ_BYTES = 1
MAX_REQ_BYTES = 1 * 1024 * 1024 * 1024  # 1 GiB
