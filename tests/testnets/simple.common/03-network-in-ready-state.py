#!/usr/bin/env python3
from argparse import RawTextHelpFormatter, ArgumentParser
from stem.control import Controller
import time
import os
import logging

logger = logging.getLogger(__name__)


def get_controller(sock_fname):
    cont = Controller.from_socket_file(path=sock_fname)
    cont.authenticate()
    return cont


def get_is_bootstrapped(cont, timeout=60):
    start_time = time.time()
    while start_time + timeout > time.time():
        line = cont.get_info('status/bootstrap-phase')
        state, _, progress, *_ = line.split()
        progress = int(progress.split('=')[1])
        if state == 'NOTICE' and progress == 100:
            logger.debug('Tor is bootstrapped')
            return True
        time.sleep(1)
    logger.debug('Tor didn\'t bootstrap before timeout. Last line: %s', line)
    return False


def get_has_full_consensus(cont, network_size, timeout=60):
    start_time = time.time()
    while start_time + timeout > time.time():
        relays = [r for r in cont.get_network_statuses()]
        if len(relays) == network_size:
            logger.debug('Tor has correct network size %d',
                         network_size)
            return True
        elif len(relays) > network_size:
            logger.warning('Tor has more relays than expected. %d vs %d',
                           len(relays), network_size)
            return True
        time.sleep(1)
    logger.debug('Tor didn\'t reach expected network size %d before '
                 'timeout', network_size)
    return False


def is_tor_ready(sock_fname, network_size):
    with get_controller(sock_fname) as cont:
        if not get_is_bootstrapped(cont):
            logger.warning('%s not bootstrapped, Tor not ready', sock_fname)
            return False
        if not get_has_full_consensus(cont, network_size):
            logger.warning('%s doesn\'t have full consensus, Tor not ready',
                           sock_fname)
            return False
    logger.info('%s is ready', sock_fname)
    return True


def main(args):
    for datadir in args.datadir:
        logger.info('Checking if %s is ready', datadir)
        sock_fname = os.path.join(datadir, 'control_socket')
        assert os.path.exists(sock_fname)
        if not is_tor_ready(sock_fname, network_size=args.size):
            return 1
    # If we got to this point, it seems like every relay is completely ready.
    # Do one more check to make sure that's still the case.
    for datadir in args.datadir:
        logger.info('Verifying %s is still ready', datadir)
        sock_fname = os.path.join(datadir, 'control_socket')
        assert os.path.exists(sock_fname)
        if not is_tor_ready(sock_fname, network_size=args.size):
            return 1
    return 0


if __name__ == '__main__':
    desc = '''
Given the data directories for a local tor network, connect to the control
socket in each directory and verify that the tor on the other end of the socket
is fully bootstrapped and has the right size of consensus.

The "right size of consensus" is determined based on the number of data
directories given to check. If that is not okay to assume (for example, there
are some Tor client [non-relay] data directories given to check), then specify
the size manually with --size.

Waits up to 60 seconds for each check for each tor.

- In the worst case, this script will take a long time to run (if every tor
  suddenly passes each check after 59 seconds).
- In the normal failure case, this script will take about 60 seconds to run
  (the first tor is not ready and fails its checks).
- In the normal case, it will run very quickly (every tor is bootstrapped and
  ready).

Exits with 0 if everything is good. Otherwise exits with a postive integer.
'''
    parser = ArgumentParser(
            formatter_class=RawTextHelpFormatter, description=desc)
    parser.add_argument('-s', '--size', type=int, help='If given, don\'t '
                        'assume the network size based on the number of '
                        'datadirs, but use this size instead.')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('datadir', nargs='+', type=str)
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if not args.size:
        args.size = len(args.datadir)

    try:
        exit(main(args))
    except KeyboardInterrupt:
        pass
