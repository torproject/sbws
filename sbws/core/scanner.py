''' Measure the relays. '''

from ..lib.circuitbuilder import GapsCircuitBuilder as CB
from ..lib.resultdump import ResultDump
from ..lib.resultdump import ResultSuccess, ResultErrorCircuit
from ..lib.resultdump import ResultErrorStream
from ..lib.relaylist import RelayList
from ..lib.relayprioritizer import RelayPrioritizer
from ..lib.destination import DestinationList
from ..util.timestamp import now_isodt_str
from ..util.state import State
from sbws.globals import fail_hard, HTTP_GET_HEADERS
import sbws.util.stem as stem_utils
import sbws.util.requests as requests_utils
from argparse import ArgumentDefaultsHelpFormatter
from multiprocessing.dummy import Pool
from threading import Event
import time
import os
import logging
import requests
import random


rng = random.SystemRandom()
end_event = Event()
log = logging.getLogger(__name__)


def timed_recv_from_server(session, dest, byte_range):
    ''' Request the **byte_range** from the URL at **dest**. If successful,
    return True and the time it took to download. Otherwise return False and an
    exception. '''

    start_time = time.time()
    HTTP_GET_HEADERS['Range'] = byte_range
    # TODO:
    # - What other exceptions can this throw?
    # - Do we have to read the content, or did requests already do so?
    try:
        # headers are merged with the session ones, not overwritten.
        session.get(dest.url, headers=HTTP_GET_HEADERS, verify=dest.verify)
    except requests.exceptions.ConnectionError as e:
        return False, e
    except requests.exceptions.ReadTimeout as e:
        return False, e
    end_time = time.time()
    return True, end_time - start_time


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
    start = rng.choice(range(0, content_length - size + 1))
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
        success, data = timed_recv_from_server(session, dest, random_range)
        if not success:
            # data is an exception
            log.warning('While measuring the RTT to %s we hit an exception '
                        '(does the webserver support Range requests?): %s',
                        dest.url, data)
            return None
        assert success
        # data is an RTT
        assert isinstance(data, float) or isinstance(data, int)
        rtts.append(data)
    return rtts


def measure_bandwidth_to_server(session, conf, dest, content_length):
    results = []
    num_downloads = conf.getint('scanner', 'num_downloads')
    expected_amount = conf.getint('scanner', 'initial_read_request')
    min_dl = conf.getint('scanner', 'min_download_size')
    max_dl = conf.getint('scanner', 'max_download_size')
    download_times = {
        'toofast': conf.getfloat('scanner', 'download_toofast'),
        'min': conf.getfloat('scanner', 'download_min'),
        'target': conf.getfloat('scanner', 'download_target'),
        'max': conf.getfloat('scanner', 'download_max'),
    }
    while len(results) < num_downloads:
        assert expected_amount >= min_dl
        assert expected_amount <= max_dl
        random_range = get_random_range_string(content_length, expected_amount)
        success, data = timed_recv_from_server(session, dest, random_range)
        if not success:
            # data is an exception
            log.warning('While measuring the bandwidth to %s we hit an '
                        'exception (does the webserver support Range '
                        'requests?): %s', dest.url, data)
            return None
        assert success
        # data is a download time
        assert isinstance(data, float) or isinstance(data, int)
        if _should_keep_result(
                expected_amount == max_dl, data, download_times):
            results.append({
                'duration': data, 'amount': expected_amount})
        expected_amount = _next_expected_amount(
            expected_amount, data, download_times, min_dl, max_dl)
    return results


def _pick_ideal_second_hop(relay, dest, rl, cont, is_exit):
    '''
    Sbws builds two hop circuits. Given the **relay** to measure with
    destination **dest**, pick a second relay that is or is not an exit
    according to **is_exit**.
    '''
    candidates = rl.exits_not_bad_allowing_port(dest.port) if is_exit \
        else rl.non_exits
    if not len(candidates):
        return None
    log.debug('Picking a 2nd hop to measure %s from %d choices. is_exit=%s',
              relay.nickname, len(candidates), is_exit)
    for min_bw_factor in [2, 1.75, 1.5, 1.25, 1]:
        min_bw = relay.consensus_bandwidth * min_bw_factor
        new_candidates = stem_utils.only_relays_with_bandwidth(
            cont, candidates, min_bw=min_bw)
        if len(new_candidates) > 0:
            chosen = rng.choice(new_candidates)
            log.debug(
                'Found %d candidate 2nd hops with at least %sx the bandwidth '
                'of %s. Returning %s (bw=%s).',
                len(new_candidates), min_bw_factor, relay.nickname,
                chosen.nickname, chosen.consensus_bandwidth)
            return chosen
    candidates = sorted(candidates, key=lambda r: r.bandwidth, reverse=True)
    chosen = candidates[0]
    log.debug(
        'Didn\'t find any 2nd hops at least as fast as %s (bw=%s). It\'s '
        'probably really fast. Returning %s (bw=%s), the fastest '
        'candidate we have.', relay.nickname, relay.consensus_bandwidth,
        chosen.nickname, chosen.consensus_bandwidth)
    return chosen


def measure_relay(args, conf, destinations, cb, rl, relay):
    s = requests_utils.make_session(
        cb.controller, conf.getfloat('general', 'http_timeout'))
    # Pick a destionation
    dest = destinations.next()
    if not dest:
        log.warning('Unable to get destination to measure %s %s',
                    relay.nickname, relay.fingerprint[0:8])
        return None
    # Pick a relay to help us measure the given relay. If the given relay is an
    # exit, then pick a non-exit. Otherwise pick an exit.
    helper = None
    circ_fps = None
    if relay.is_exit_not_bad_allowing_port(dest.port):
        helper = _pick_ideal_second_hop(
            relay, dest, rl, cb.controller, is_exit=False)
        if helper:
            circ_fps = [helper.fingerprint, relay.fingerprint]
    else:
        helper = _pick_ideal_second_hop(
            relay, dest, rl, cb.controller, is_exit=True)
        if helper:
            circ_fps = [relay.fingerprint, helper.fingerprint]
    if not helper:
        # TODO: Return ResultError of some sort
        log.warning('Unable to pick a 2nd hop to help measure %s %s',
                    relay.nickname, relay.fingerprint[0:8])
        return None
    assert helper
    assert circ_fps is not None and len(circ_fps) == 2
    # Build the circuit
    our_nick = conf['scanner']['nickname']
    circ_id = cb.build_circuit(circ_fps)
    if not circ_id:
        log.warning('Could not build circuit involving %s', relay.nickname)
        msg = 'Unable to complete circuit'
        return [
            ResultErrorCircuit(relay, circ_fps, dest.url, our_nick, msg=msg),
        ]
    log.debug('Built circ %s %s for relay %s %s', circ_id,
              stem_utils.circuit_str(cb.controller, circ_id), relay.nickname,
              relay.fingerprint[0:8])
    # Make a connection to the destionation webserver and make sure it can
    # still help us measure
    is_usable, usable_data = dest.is_usable(circ_id, s, cb.controller)
    if not is_usable:
        log.warning('When measuring %s %s the destination seemed to have '
                    'stopped being usable: %s', relay.nickname,
                    relay.fingerprint[0:8], usable_data)
        cb.close_circuit(circ_id)
        # TODO: Return a different/new type of ResultError?
        msg = 'The destination seemed to have stopped being usable'
        return [
            ResultErrorStream(relay, circ_fps, dest.url, our_nick, msg=msg),
        ]
    assert is_usable
    assert 'content_length' in usable_data
    # FIRST: measure RTT
    rtts = measure_rtt_to_server(s, conf, dest, usable_data['content_length'])
    if rtts is None:
        log.warning('Unable to measure RTT to %s via relay %s %s',
                    dest.url, relay.nickname, relay.fingerprint[0:8])
        cb.close_circuit(circ_id)
        # TODO: Return a different/new type of ResultError?
        msg = 'Something bad happened while measuring RTTs'
        return [
            ResultErrorStream(relay, circ_fps, dest.url, our_nick, msg=msg),
        ]
    # SECOND: measure bandwidth
    bw_results = measure_bandwidth_to_server(
        s, conf, dest, usable_data['content_length'])
    if bw_results is None:
        log.warning('Unable to measure bandwidth to %s via relay %s %s',
                    dest.url, relay.nickname, relay.fingerprint[0:8])
        cb.close_circuit(circ_id)
        # TODO: Return a different/new type of ResultError?
        msg = 'Something bad happened while measuring bandwidth'
        return [
            ResultErrorStream(relay, circ_fps, dest.url, our_nick, msg=msg),
        ]
    cb.close_circuit(circ_id)
    # Finally: store result
    return [
        ResultSuccess(rtts, bw_results, relay, circ_fps, dest.url, our_nick),
    ]


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


def _next_expected_amount(expected_amount, result_time, download_times,
                          min_dl, max_dl):
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
    expected_amount = max(min_dl, expected_amount)
    expected_amount = min(max_dl, expected_amount)
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


def run_speedtest(args, conf):
    controller, _ = stem_utils.init_controller(
        path=conf.getpath('tor', 'control_socket'))
    if not controller:
        controller = stem_utils.launch_tor(conf)
    else:
        log.warning(
            'Is sbws already running? '
            'We found an existing Tor process at %s. We are not going to '
            'launch Tor, nor are we going to try to configure it to behave '
            'like we expect. This might work okay, but it also might not. '
            'If you experience problems, you should try letting sbws launch '
            'Tor for itself. The ability to use an already running Tor only '
            'exists for sbws developers. It is expected to be broken and may '
            'even lead to messed up results.',
            conf.getpath('tor', 'control_socket'))
        time.sleep(15)
    rl = RelayList(args, conf, controller)
    cb = CB(args, conf, controller, rl)
    rd = ResultDump(args, conf, end_event)
    rp = RelayPrioritizer(args, conf, rl, rd)
    destinations, error_msg = DestinationList.from_config(
        conf, cb, rl, controller)
    if not destinations:
        fail_hard(error_msg)
    max_pending_results = conf.getint('scanner', 'measurement_threads')
    pool = Pool(max_pending_results)
    pending_results = []
    while True:
        num_relays = 0
        loop_tstart = time.time()
        for target in rp.best_priority():
            num_relays += 1
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
        while len(pending_results) > 0:
            time.sleep(5)
            pending_results = [r for r in pending_results if not r.ready()]
        loop_tstop = time.time()
        loop_tdelta = (loop_tstop - loop_tstart) / 60
        log.debug("Measured %s relays in %s minutes", num_relays, loop_tdelta)


def gen_parser(sub):
    d = 'The scanner side of sbws. This should be run on a well-connected '\
        'machine on the Internet with a healthy amount of spare bandwidth. '\
        'This continuously builds circuits, measures relays, and dumps '\
        'results into a datadir, commonly found in ~/.sbws'
    sub.add_parser('scanner', formatter_class=ArgumentDefaultsHelpFormatter,
                   description=d)


def main(args, conf):
    if conf.getint('scanner', 'measurement_threads') < 1:
        fail_hard('Number of measurement threads must be larger than 1')

    min_dl = conf.getint('scanner', 'min_download_size')
    max_dl = conf.getint('scanner', 'max_download_size')
    if max_dl < min_dl:
        fail_hard('Max download size %d cannot be smaller than min %d',
                  max_dl, min_dl)

    os.makedirs(conf.getpath('paths', 'datadir'), exist_ok=True)

    state = State(conf.getpath('paths', 'state_fname'))
    state['scanner_started'] = now_isodt_str()

    try:
        run_speedtest(args, conf)
    except KeyboardInterrupt as e:
        raise e
    finally:
        end_event.set()
