''' Measure the relays. '''

from ..lib.circuitbuilder import FooCircuitBuilder as CB
from ..lib.resultdump import ResultDump
# from ..lib.resultdump import ResultSuccess
# from ..lib.resultdump import ResultErrorCircuit
# from ..lib.resultdump import ResultErrorAuth
from ..lib.relaylist import RelayList
from ..lib.relayprioritizer import RelayPrioritizer
from ..lib.destination import DestinationList
# from ..util.simpleauth import authenticate_to_server
# from ..util.sockio import (make_socket, close_socket)
from sbws.globals import (fail_hard, is_initted)
from sbws.globals import MIN_REQ_BYTES, MAX_REQ_BYTES
import sbws.util.stem as stem_utils
from stem.control import EventType
from argparse import ArgumentDefaultsHelpFormatter
from multiprocessing.dummy import Pool
from threading import Event
import socket
import time
import os
import logging
import requests
import random

end_event = Event()
log = logging.getLogger(__name__)


def timed_recv_from_server(sock, conf, yet_to_read):
    ''' Return the time in seconds it took to read <yet_to_read> bytes from
    the server. Return None if error '''
    assert yet_to_read > 0
    start_time = time.time()
    while yet_to_read > 0:
        limit = min(conf.getint('scanner', 'max_recv_per_read'), yet_to_read)
        try:
            read_this_time = len(sock.recv(limit))
        except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
            log.info(e)
            return
        if read_this_time == 0:
            return
        yet_to_read -= read_this_time
    end_time = time.time()
    return end_time - start_time


def get_random_range_string(content_length, size):
    '''
    Return a random range of bytes of length **size**. **content_length** is
    the size of the file we will be requesting a range of bytes from.

    For example, for content_length of 100 and size 10, this function will
    return one of the following: '0-9', '1-10', '2-11', [...] '89-98', '90-99'
    '''
    assert size <= content_length
    # start can be anywhere in the content_length as long as it is **size**
    # bytes away from the end or more. Because range is [start, end) (doesn't
    # include the end value), add 1 to the end.
    start = random.choice(range(0, content_length - size + 1))
    # Unlike range, the byte range in an http header is [start, end] (does
    # include the end value), so we subtract one
    end = start + size - 1
    # start and end are indexes, while content_length is a length, therefore,
    # the largest index end should ever be should be less than the total length
    # of the content. For example, if content_length is 10, end could be
    # anywhere from 0 to 9.
    assert end < content_length
    return 'bytes={}-{}'.format(start, end)


def measure_rtt_to_server(session, conf, dest, content_length):
    ''' Make multiple end-to-end RTT measurements by making small HTTP requests
    over a circuit + stream that should already exist, persist, and not need
    rebuilding. If something goes wrong and not all of the RTT measurements can
    be made, return None. Otherwise return a list of the RTTs (in seconds). '''
    rtts = []
    size = conf.getint('scanner', 'min_download_size')
    log.debug('Measuring RTT to %s', dest.url)
    for _ in range(0, conf.getint('scanner', 'num_rtts')):
        random_range = get_random_range_string(content_length, size)
        headers = {'Range': random_range}
        start_time = time.time()
        # TODO:
        # - What other exceptions can this throw?
        # - Do we have to read the content, or did requests already do so?
        # - Add timeout
        try:
            session.get(dest.url, headers=headers)
        except requests.exceptions.ConnectionError as e:
            log.error('While measuring RTT to %s we hit an exception (does '
                      'the webserver support Range requests?): %s', dest.url,
                      e)
            return None
        end_time = time.time()
        rtts.append(end_time - start_time)
    return rtts


def connect_to_destination_over_circuit(dest, circ_id, session, cont, conf):
    '''
    Connect to **dest* over the given **circ_id** using the given Requests
    **session**. Make sure everything seems in order. Return True and a
    dictionary of helpful information if we connected and everything looks
    fine.  Otherwise return False and a string stating what the issue is.

    :param dest Destination: the place to which we should connect
    :param circ_id str: the circuit we should connect over
    :param session Session: the Requests library session object to use to make
        the connection.
    :param cont Controller: them Stem library controller controlling Tor
    :returns: True and a dictionary if everything is in order and measurements
        should commence.  False and an error string otherwise.
    '''
    error_prefix = 'When sending HTTP HEAD to {}, '.format(dest.url)
    with stem_utils.stream_building_lock:
        listener = stem_utils.attach_stream_to_circuit_listener(cont, circ_id)
        stem_utils.add_event_listener(cont, listener, EventType.STREAM)
        try:
            # TODO:
            # - What other exceptions can this throw?
            # - Add timeout
            head = session.head(dest.url)
        except requests.exceptions.ConnectionError as e:
            return False, 'Could not connect to {} over circ {}: {}'.format(
                dest.url, circ_id, e)
        stem_utils.remove_event_listener(cont, listener)
    if head.status_code != requests.codes.ok:
        return False, error_prefix + 'we expected HTTP code '\
            '{} not {}'.format(dest.url, requests.codes.ok, head.status_code)
    if 'content-length' not in head.headers:
        return False, error_prefix + 'we except the header Content-Length '\
                'to exist in the response'
    max_dl = conf.getint('scanner', 'max_download_size')
    content_length = int(head.headers['content-length'])
    if max_dl > content_length:
        return False, error_prefix + 'our maximum configured download size '\
            'is {} but the content is only {}'.format(max_dl, content_length)
    log.debug('Connected to %s over circuit %s', dest.url, circ_id)
    return True, {'content_length': content_length}


def measure_relay(args, conf, destinations, cb, rl, relay):
    s = requests.Session()
    s.proxies = {
        'http': 'socks5h://{}:{}'.format(conf['tor']['socks_host'],
                                         conf.getint('tor', 'socks_port')),
        'https': 'socks5h://{}:{}'.format(conf['tor']['socks_host'],
                                          conf.getint('tor', 'socks_port')),
    }
    dest = destinations.next()
    if not dest:
        log.warning('Unable to get destination to measure %s %s',
                    relay.nickname, relay.fingerprint[0:8])
        return None
    circ_id = cb.build_circuit([relay.fingerprint])
    if not circ_id:
        log.warning('Could not build circuit involving %s', relay.nickname)
        # TODO: Return ResultError of some sort
        return None
    log.debug('Built circ %s for relay %s %s', circ_id, relay.nickname,
              relay.fingerprint[0:8])
    success, details = connect_to_destination_over_circuit(
        dest, circ_id, s, cb.controller, conf)
    if not success:
        log.warning('When measuring %s %s: %s', relay.nickname,
                    relay.fingerprint[0:8], details)
        cb.close_circuit(circ_id)
        # TODO: Return ResultError of some sort???
        return None
    assert success
    assert 'content_length' in details
    rtts = measure_rtt_to_server(s, conf, dest, details['content_length'])
    log.debug(rtts)
    cb.close_circuit(circ_id)


def dispatch_worker_thread(*a, **kw):
    try:
        return measure_relay(*a, **kw)
    except Exception as err:
        log.exception('Unhandled exception in worker thread')
        raise err


def _should_keep_result(did_request_maximum, result_time, download_times):
    # In the normal case, we didn't ask for the maximum allowed amount. So we
    # should only allow ourselves to keep results that are between the min and
    # max allowed time
    if not did_request_maximum and \
            result_time >= download_times['min'] and \
            result_time < download_times['max']:
        return True
    # If we did request the maximum amount, we should keep the result as long
    # as it took less than the maximum amount of time
    if did_request_maximum and \
            result_time < download_times['max']:
        return True
    # In all other cases, return false
    log.debug('Not keeping result time %f.%s', result_time,
              '' if not did_request_maximum else ' We requested the maximum '
              'amount allowed.')
    return False


def _next_expected_amount(expected_amount, result_time, download_times):
    if result_time < download_times['toofast']:
        # Way too fast, greatly increase the amount we ask for
        expected_amount = int(expected_amount * 5)
    elif result_time < download_times['min'] or \
            result_time >= download_times['max']:
        # As long as the result is between min/max, keep the expected amount
        # the same. Otherwise, adjust so we are aiming for the target amount.
        expected_amount = int(
            expected_amount * download_times['target'] / result_time)
    # Make sure we don't request too much or too little
    expected_amount = max(MIN_REQ_BYTES, expected_amount)
    expected_amount = min(MAX_REQ_BYTES, expected_amount)
    return expected_amount


def result_putter(result_dump):
    ''' Create a function that takes a single argument -- the measurement
    result -- and return that function so it can be used by someone else '''
    def closure(measurement_result):
        return result_dump.queue.put(measurement_result)
    return closure


def result_putter_error(target):
    ''' Create a function that takes a single argument -- an error from a
    measurement -- and return that function so it can be used by someone else
    '''
    def closure(err):
        log.error('Unhandled exception caught while measuring %s: %s %s',
                  target.nickname, type(err), err)
    return closure


def run_speedtest2(args, conf):
    controller, error_msg = stem_utils.init_controller_with_config(conf)
    if not controller:
        fail_hard(error_msg)
    assert controller
    cb = CB(args, conf, controller=controller)
    rl = RelayList(args, conf, controller=controller)
    rd = ResultDump(args, conf, end_event)
    rp = RelayPrioritizer(args, conf, rl, rd)
    destinations, error_msg = DestinationList.from_config(conf)
    if not destinations:
        fail_hard(error_msg)
    max_pending_results = conf.getint('scanner', 'measurement_threads')
    pool = Pool(max_pending_results)
    pending_results = []
    while True:
        for target in rp.best_priority():
            log.debug('Measuring %s %s', target.nickname,
                      target.fingerprint[0:8])
            callback = result_putter(rd)
            callback_err = result_putter_error(target)
            async_result = pool.apply_async(
                dispatch_worker_thread,
                [args, conf, destinations, cb, rl, target],
                {}, callback, callback_err)
            pending_results.append(async_result)
            while len(pending_results) >= max_pending_results:
                time.sleep(5)
                pending_results = [r for r in pending_results if not r.ready()]


def gen_parser(sub):
    d = 'The scanner side of sbws. This should be run on a well-connected '\
        'machine on the Internet with a healthy amount of spare bandwidth. '\
        'This continuously builds circuits, measures relays, and dumps '\
        'results into a datadir, commonly found in ~/.sbws'
    sub.add_parser('scanner', formatter_class=ArgumentDefaultsHelpFormatter,
                   description=d)


def main(args, conf):
    if not is_initted(args.directory):
        fail_hard('Sbws isn\'t initialized. Try sbws init')

    if conf.getint('scanner', 'measurement_threads') < 1:
        fail_hard('Number of measurement threads must be larger than 1')

    min_dl = conf.getint('scanner', 'min_download_size')
    max_dl = conf.getint('scanner', 'max_download_size')
    if max_dl < min_dl:
        fail_hard('Max download size %d cannot be smaller than min %d',
                  max_dl, min_dl)

    if conf['tor']['control_type'] not in ['port', 'socket']:
        fail_hard('Must specify either control port or socket. '
                  'Not "%s"', conf['tor']['control_type'])
    if conf['tor']['control_type'] == 'port':
        try:
            conf.getint('tor', 'control_location')
        except ValueError as e:
            fail_hard('Couldn\'t read control port from config: %s', e)
    os.makedirs(conf['paths']['datadir'], exist_ok=True)

    try:
        run_speedtest2(args, conf)
    except KeyboardInterrupt as e:
        raise e
    finally:
        end_event.set()
