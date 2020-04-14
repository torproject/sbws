''' Measure the relays. '''
import queue

import signal
import sys
import threading
import traceback
import uuid

from multiprocessing.context import TimeoutError

from ..lib.circuitbuilder import GapsCircuitBuilder as CB
from ..lib.resultdump import ResultDump
from ..lib.resultdump import (
    ResultSuccess, ResultErrorCircuit, ResultErrorStream,
    ResultErrorSecondRelay,  ResultError, ResultErrorDestination
    )
from ..lib.relaylist import RelayList
from ..lib.relayprioritizer import RelayPrioritizer
from ..lib.destination import (DestinationList,
                               connect_to_destination_over_circuit)
from ..util.timestamp import now_isodt_str
from ..util.state import State
from sbws.globals import fail_hard, HTTP_GET_HEADERS, TIMEOUT_MEASUREMENTS
import sbws.util.stem as stem_utils
import sbws.util.requests as requests_utils
from argparse import ArgumentDefaultsHelpFormatter
from multiprocessing.dummy import Pool
import time
import os
import logging
import random

from .. import settings
from ..lib.heartbeat import Heartbeat

rng = random.SystemRandom()
log = logging.getLogger(__name__)
# Declare the objects that manage the threads global so that sbws can exit
# gracefully at any time.
pool = None
rd = None
controller = None

FILLUP_TICKET_MSG = """Something went wrong.
Please create a ticket in https://trac.torproject.org with this traceback."""


def stop_threads(signal, frame, exit_code=0):
    global rd, pool
    log.debug('Stopping sbws.')
    # Avoid new threads to start.
    settings.set_end_event()
    # Stop Pool threads
    pool.close()
    pool.join()
    # Stop ResultDump thread
    rd.thread.join()
    # Stop Tor thread
    controller.close()
    sys.exit(exit_code)


signal.signal(signal.SIGTERM, stop_threads)


def dumpstacks():
    log.critical(FILLUP_TICKET_MSG)
    thread_id2name = dict([(t.ident, t.name) for t in threading.enumerate()])
    for thread_id, stack in sys._current_frames().items():
        log.critical("Thread: %s(%d)",
                     thread_id2name.get(thread_id, ""), thread_id)
        log.critical(traceback.format_stack("".join(stack)))
    # If logging level is less than DEBUG (more verbose), start pdb so that
    # developers can debug the issue.
    if log.getEffectiveLevel() < logging.DEBUG:
        import pdb
        pdb.set_trace()
    # Otherwise exit.
    else:
        # Change to stop threads when #28869 is merged
        sys.exit(1)


def timed_recv_from_server(session, dest, byte_range):
    ''' Request the **byte_range** from the URL at **dest**. If successful,
    return True and the time it took to download. Otherwise return False and an
    exception. '''

    start_time = time.time()
    HTTP_GET_HEADERS['Range'] = byte_range
    # - response.elapsed "measures the time taken between sending the first
    #   byte of the request and finishing parsing the headers.
    #   It is therefore unaffected by consuming the response content"
    #   If this mean that the content has arrived, elapsed could be used to
    #   know the time it took.
    try:
        # headers are merged with the session ones, not overwritten.
        session.get(dest.url, headers=HTTP_GET_HEADERS, verify=dest.verify)
    # All `requests` exceptions could be caught with
    # `requests.exceptions.RequestException`, but it seems that `requests`
    # does not catch all the ssl exceptions and urllib3 doesn't seem to have
    # a base exception class.
    except Exception as e:
        log.debug(e)
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
    be made, return None. Otherwise return a list of the RTTs (in seconds).

    :returns tuple: results or None if the if the measurement fail.
        None or exception if the measurement fail.

    '''
    rtts = []
    size = conf.getint('scanner', 'min_download_size')
    for _ in range(0, conf.getint('scanner', 'num_rtts')):
        log.debug('Measuring RTT to %s', dest.url)
        random_range = get_random_range_string(content_length, size)
        success, data = timed_recv_from_server(session, dest, random_range)
        if not success:
            # data is an exception
            log.debug('While measuring the RTT to %s we hit an exception '
                      '(does the webserver support Range requests?): %s',
                      dest.url, data)
            return None, data
        assert success
        # data is an RTT
        assert isinstance(data, float) or isinstance(data, int)
        rtts.append(data)
    return rtts, None


def measure_bandwidth_to_server(session, conf, dest, content_length):
    """
    :returns tuple: results or None if the if the measurement fail.
        None or exception if the measurement fail.

    """
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
    while len(results) < num_downloads and not settings.end_event.is_set():
        assert expected_amount >= min_dl
        assert expected_amount <= max_dl
        random_range = get_random_range_string(content_length, expected_amount)
        success, data = timed_recv_from_server(session, dest, random_range)
        if not success:
            # data is an exception
            log.debug('While measuring the bandwidth to %s we hit an '
                      'exception (does the webserver support Range '
                      'requests?): %s', dest.url, data)
            return None, data
        assert success
        # data is a download time
        assert isinstance(data, float) or isinstance(data, int)
        if _should_keep_result(
                expected_amount == max_dl, data, download_times):
            results.append({
                'duration': data, 'amount': expected_amount})
        expected_amount = _next_expected_amount(
            expected_amount, data, download_times, min_dl, max_dl)
    return results, None


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
    min_relay_bw = rl.exit_min_bw() if is_exit else rl.non_exit_min_bw()
    log.debug('Picking a 2nd hop to measure %s from %d choices. is_exit=%s',
              relay.nickname, len(candidates), is_exit)
    for min_bw_factor in [2, 1.75, 1.5, 1.25, 1]:
        min_bw = relay.consensus_bandwidth * min_bw_factor
        # We might have a really slow/new relay. Try to measure it properly by
        # using only relays with or above our calculated min_relay_bw (see:
        # _calculate_min_bw_second_hop() in relaylist.py).
        if min_bw < min_relay_bw:
            min_bw = min_relay_bw
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
    candidates = sorted(candidates, key=lambda r: r.consensus_bandwidth,
                        reverse=True)
    chosen = candidates[0]
    log.debug(
        'Didn\'t find any 2nd hops at least as fast as %s (bw=%s). It\'s '
        'probably really fast. Returning %s (bw=%s), the fastest '
        'candidate we have.', relay.nickname, relay.consensus_bandwidth,
        chosen.nickname, chosen.consensus_bandwidth)
    return chosen


def measure_relay(args, conf, destinations, cb, rl, relay):
    """
    Select a Web server, a relay to build the circuit,
    build the circuit and measure the bandwidth of the given relay.

    :return Result: a measurement Result object

    """
    log.debug('Measuring %s %s', relay.nickname, relay.fingerprint)
    our_nick = conf['scanner']['nickname']
    s = requests_utils.make_session(
        cb.controller, conf.getfloat('general', 'http_timeout'))
    # Probably because the scanner is stopping.
    if s is None:
        if settings.end_event.is_set():
            return None
        else:
            # In future refactor this should be returned from the make_session
            reason = "Unable to get proxies."
            log.debug(reason + ' to measure %s %s',
                      relay.nickname, relay.fingerprint)
            return [
                ResultError(relay, [], '', our_nick,
                            msg=reason),
                ]
    # Pick a destionation
    dest = destinations.next()
    # When there're no any functional destinations.
    if not dest:
        # NOTE: When there're still functional destinations but only one of
        # them fail, the error will be included in `ResultErrorStream`.
        # Since this is being executed in a thread, the scanner can not
        # be stop here, but the `end_event` signal can be set so that the
        # main thread stop the scanner.
        # It might be useful to store the fact that the destinations fail,
        # so store here the error, and set the signal once the error is stored
        # (in `resultump`).
        log.critical("There are not any functional destinations.\n"
                     "It is recommended to set several destinations so that "
                     "the scanner can continue if one fails.")
        reason = "No functional destinations"
        # Resultdump will set end_event after storing the error
        return [
            ResultErrorDestination(relay, [], '', our_nick, msg=reason),
        ]

    # Pick a relay to help us measure the given relay. If the given relay is an
    # exit, then pick a non-exit. Otherwise pick an exit.
    helper = None
    circ_fps = None
    if relay.is_exit_not_bad_allowing_port(dest.port):
        helper = _pick_ideal_second_hop(
            relay, dest, rl, cb.controller, is_exit=False)
        if helper:
            circ_fps = [helper.fingerprint, relay.fingerprint]
            # stored for debugging
            nicknames = [helper.nickname, relay.nickname]
    else:
        helper = _pick_ideal_second_hop(
            relay, dest, rl, cb.controller, is_exit=True)
        if helper:
            circ_fps = [relay.fingerprint, helper.fingerprint]
            nicknames = [relay.nickname, helper.nickname]
    if not helper:
        reason = 'Unable to select a second relay'
        log.debug(reason + ' to help measure %s (%s)',
                  relay.fingerprint, relay.nickname)
        return [
            ResultErrorSecondRelay(relay, [], dest.url, our_nick,
                                   msg=reason),
            ]

    # Build the circuit
    circ_id, reason = cb.build_circuit(circ_fps)
    if not circ_id:
        log.debug('Could not build circuit with path %s (%s): %s ',
                  circ_fps, nicknames, reason)
        return [
            ResultErrorCircuit(relay, circ_fps, dest.url, our_nick,
                               msg=reason),
        ]
    log.debug('Built circuit with path %s (%s) to measure %s (%s)',
              circ_fps, nicknames, relay.fingerprint, relay.nickname)
    # Make a connection to the destination
    is_usable, usable_data = connect_to_destination_over_circuit(
        dest, circ_id, s, cb.controller, dest._max_dl)
    if not is_usable:
        log.debug('Destination %s unusable via circuit %s (%s), %s',
                  dest.url, circ_fps, nicknames, usable_data)
        cb.close_circuit(circ_id)
        return [
            ResultErrorStream(relay, circ_fps, dest.url, our_nick,
                              msg=usable_data),
        ]
    assert is_usable
    assert 'content_length' in usable_data
    # FIRST: measure RTT
    rtts, reason = measure_rtt_to_server(s, conf, dest,
                                         usable_data['content_length'])
    if rtts is None:
        log.debug('Unable to measure RTT for %s (%s) to %s via circuit '
                  '%s (%s): %s', relay.fingerprint, relay.nickname,
                  dest.url, circ_fps, nicknames, reason)
        cb.close_circuit(circ_id)
        return [
            ResultErrorStream(relay, circ_fps, dest.url, our_nick,
                              msg=str(reason)),
        ]
    # SECOND: measure bandwidth
    bw_results, reason = measure_bandwidth_to_server(
        s, conf, dest, usable_data['content_length'])
    if bw_results is None:
        log.debug('Unable to measure bandwidth for %s (%s) to %s via circuit '
                  '%s (%s): %s', relay.fingerprint, relay.nickname,
                  dest.url, circ_fps, nicknames, reason)
        cb.close_circuit(circ_id)
        return [
            ResultErrorStream(relay, circ_fps, dest.url, our_nick,
                              msg=str(reason)),
        ]
    cb.close_circuit(circ_id)
    # Finally: store result
    log.debug('Success measurement for %s (%s) via circuit %s (%s) to %s',
              relay.fingerprint, relay.nickname, circ_fps, nicknames, dest.url)
    return [
        ResultSuccess(rtts, bw_results, relay, circ_fps, dest.url, our_nick),
    ]


def dispatch_worker_thread(*a, **kw):
    # If at the point where the relay is actually going to be measured there
    # are not any functional destinations or the `end_event` is set, do not
    # try to start measuring the relay, since it will fail anyway.
    try:
        # a[2] is the argument `destinations`
        functional_destinations = a[2].functional_destinations
    # In case the arguments or the method change, catch the possible exceptions
    # but ignore here that there are not destinations.
    except (IndexError, TypeError):
        log.debug("Wrong argument or attribute.")
        functional_destinations = True
    if not functional_destinations or settings.end_event.is_set():
        return None
    return measure_relay(*a, **kw)


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
        # Since result_dump thread is calling queue.get() every second,
        # the queue should be full for only 1 second.
        # This call blocks at maximum timeout seconds.
        try:
            result_dump.queue.put(measurement_result, timeout=3)
        except queue.Full:
            # The result would be lost, the scanner will continue working.
            log.warning(
                "The queue with measurements is full, when adding %s.\n"
                "It is possible that the thread that get them to "
                "write them to the disk (ResultDump.enter) is stalled.",
                measurement_result
                )
    return closure


def result_putter_error(target):
    ''' Create a function that takes a single argument -- an error from a
    measurement -- and return that function so it can be used by someone else
    '''
    def closure(object):
        if settings.end_event.is_set():
            return
        # The only object that can be here if there is not any uncatched
        # exception is stem.SocketClosed when stopping sbws
        # An exception here means that the worker thread finished.
        log.warning(FILLUP_TICKET_MSG)
        # To print the traceback that happened in the thread, not here in
        # the main process.
        log.warning("".join(traceback.format_exception(
            type(object), object, object.__traceback__))
            )
    return closure


def main_loop(args, conf, controller, relay_list, circuit_builder, result_dump,
              relay_prioritizer, destinations, pool):
    """Starts and reuse the threads that measure the relays forever.

    It starts a loop that will be run while there is not and event signaling
    that sbws is stopping (because of SIGTERM or SIGINT).

    Then, it starts a second loop with an ordered list (generator) of relays
    to measure that might a subset of all the current relays in the Network.

    For every relay, it starts a new thread which runs ``measure_relay`` to
    measure the relay until there are ``max_pending_results`` threads.
    After that, it will reuse a thread that has finished for every relay to
    measure.
    It is the the pool method ``apply_async`` which starts or reuse a thread.
    This method returns an ``ApplyResult`` immediately, which has a ``ready``
    methods that tells whether the thread has finished or not.

    When the thread finish, ie. ``ApplyResult`` is ``ready``, it triggers
    ``result_putter`` callback, which put the ``Result`` in ``ResultDump``
    queue and complete immediately.

    ``ResultDump`` thread (started before and out of this function) will get
    the ``Result`` from the queue and write it to disk, so this doesn't block
    the measurement threads.

    If there was an exception not catched by ``measure_relay``, it will call
    instead ``result_putter_error``, which logs the error and complete
    immediately.

    Before the outer loop iterates, it waits (non blocking) that all
    the ``Results`` are ready calling ``wait_for_results``.
    This avoid to start measuring the same relay which might still being
    measured.

    """
    hbeat = Heartbeat(conf.getpath('paths', 'state_fname'))

    # Set the time to wait for a thread to finish as the half of an HTTP
    # request timeout.
    # Do not start a new loop if sbws is stopping.
    while not settings.end_event.is_set():
        log.debug("Starting a new measurement loop.")
        num_relays = 0
        # Since loop might finish before pending_results is 0 due waiting too
        # long, set it here and not outside the loop.
        pending_results = []
        loop_tstart = time.time()

        # Register relay fingerprints to the heartbeat module
        hbeat.register_consensus_fprs(relay_list.relays_fingerprints)

        for target in relay_prioritizer.best_priority():
            # Don't start measuring a relay if sbws is stopping.
            if settings.end_event.is_set():
                break
            relay_list.increment_recent_measurement_attempt()
            target.increment_relay_recent_measurement_attempt()
            num_relays += 1
            # callback and callback_err must be non-blocking
            callback = result_putter(result_dump)
            callback_err = result_putter_error(target)
            async_result = pool.apply_async(
                dispatch_worker_thread,
                [args, conf, destinations, circuit_builder, relay_list,
                 target], {}, callback, callback_err)
            pending_results.append(async_result)

            # Register this measurement to the heartbeat module
            hbeat.register_measured_fpr(target.fingerprint)

        # After the for has finished, the pool has queued all the relays
        # and pending_results has the list of all the AsyncResults.
        # It could also be obtained with pool._cache, which contains
        # a dictionary with AsyncResults as items.
        num_relays_to_measure = len(pending_results)
        wait_for_results(num_relays_to_measure, pending_results)

        # Print the heartbeat message
        hbeat.print_heartbeat_message()

        loop_tstop = time.time()
        loop_tdelta = (loop_tstop - loop_tstart) / 60
        # At this point, we know the relays that were queued to be measured.
        # That does not mean they were actually measured.
        log.debug("Attempted to measure %s relays in %s minutes",
                  num_relays, loop_tdelta)
        # In a testing network, exit after first loop
        if controller.get_conf('TestingTorNetwork') == '1':
            log.info("In a testing network, exiting after the first loop.")
            # Threads should be closed nicely in some refactor
            stop_threads(signal.SIGTERM, None)


def wait_for_results(num_relays_to_measure, pending_results):
    """Wait for the pool to finish and log progress.

    While there are relays being measured, just log the progress
    and sleep :const:`~sbws.globals.TIMEOUT_MEASUREMENTS` (3mins),
    which is aproximately the time it can take to measure a relay in
    the worst case.

    When there has not been any relay measured in ``TIMEOUT_MEASUREMENTS``
    and there are still relays pending to be measured, it means there is no
    progress and call :func:`~sbws.core.scanner.force_get_results`.

    This can happen in the case of a bug that makes either
    :func:`~sbws.core.scanner.measure_relay`,
    :func:`~sbws.core.scanner.result_putter` (callback) and/or
    :func:`~sbws.core.scanner.result_putter_error` (callback error) stall.

    .. note:: in a future refactor, this could be simpler by:

      1. Initializing the pool at the begingging of each loop
      2. Callling :meth:`~Pool.close`; :meth:`~Pool.join` after
         :meth:`~Pool.apply_async`,
         to ensure no new jobs are added until the pool has finished with all
         the ones in the queue.

      As currently, there would be still two cases when the pool could stall:

      1. There's an exception in ``measure_relay`` and another in
         ``callback_err``
      2. There's an exception ``callback``.

      This could also be simpler by not having callback and callback error in
      ``apply_async`` and instead just calling callback with the
      ``pending_results``.

      (callback could be also simpler by not having a thread and queue and
      just storing to disk, since the time to write to disk is way smaller
      than the time to request over the network.)
    """
    num_last_measured = 1
    while num_last_measured > 0 and not settings.end_event.is_set():
        log.info("Pending measurements: %s out of %s: ",
                 len(pending_results), num_relays_to_measure)
        time.sleep(TIMEOUT_MEASUREMENTS)
        old_pending_results = pending_results
        pending_results = [r for r in pending_results if not r.ready()]
        num_last_measured = len(old_pending_results) - len(pending_results)
    if len(pending_results) > 0:
        force_get_results(pending_results)


def force_get_results(pending_results):
    """Try to get either the result or an exception, which gets logged.

    It is call by :func:`~sbws.core.scanner.wait_for_results` when
    the time waiting for the results was long.

    To get either the :class:`~sbws.lib.resultdump.Result` or an exception,
    call :meth:`~AsyncResult.get` with timeout.
    Timeout is low since we already waited.

    ``get`` is not call before, because it blocks and the callbacks
    are not call.
    """
    log.debug("Forcing get")
    for r in pending_results:
        try:
            result = r.get(timeout=0.1)
            log.warning("Result %s was not stored, it took too long.",
                        result)
        # TimeoutError is raised when the result is not ready, ie. has not
        # been processed yet
        except TimeoutError:
            log.warning("A result was not stored, it was not ready.")
        # If the result raised an exception, `get` returns it,
        # then log any exception so that it can be fixed.
        # This should not happen, since `callback_err` would have been call
        # first.
        except Exception as e:
            log.critical(FILLUP_TICKET_MSG)
            # If the exception happened in the threads, `log.exception` does
            # not have the traceback.
            # Using `format_exception` instead of of `print_exception` to show
            # the traceback in all the log handlers.
            log.warning("".join(traceback.format_exception(
                        type(e), e, e.__traceback__)))


def run_speedtest(args, conf):
    """Initializes all the data and threads needed to measure the relays.

    It launches or connect to Tor in a thread.
    It initializes the list of relays seen in the Tor network.
    It starts a thread to read the previous measurements and wait for new
    measurements to write them to the disk.
    It initializes a class that will be used to order the relays depending
    on their measurements age.
    It initializes the list of destinations that will be used for the
    measurements.
    It initializes the thread pool that will launch the measurement threads.
    The pool starts 3 other threads that are not the measurement (worker)
    threads.
    Finally, it calls the function that will manage the measurement threads.

    """
    global rd, pool, controller
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

    # When there will be a refactor where conf is global, this can be removed
    # from here.
    state = State(conf.getpath('paths', 'state_fname'))
    # XXX: tech-debt: create new function to obtain the controller and to
    # write the state, so that a unit test to check the state tor version can
    # be created
    # Store tor version whenever the scanner starts.
    state['tor_version'] = str(controller.get_version())
    # Call only once to initialize http_headers
    settings.init_http_headers(conf.get('scanner', 'nickname'), state['uuid'],
                               state['tor_version'])
    # To do not have to pass args and conf to RelayList, pass an extra
    # argument with the data_period
    measurements_period = conf.getint('general', 'data_period')
    rl = RelayList(args, conf, controller, measurements_period, state)
    cb = CB(args, conf, controller, rl)
    rd = ResultDump(args, conf)
    rp = RelayPrioritizer(args, conf, rl, rd)
    destinations, error_msg = DestinationList.from_config(
        conf, cb, rl, controller)
    if not destinations:
        fail_hard(error_msg)
    max_pending_results = conf.getint('scanner', 'measurement_threads')
    pool = Pool(max_pending_results)
    try:
        main_loop(args, conf, controller, rl, cb, rd, rp, destinations, pool)
    except KeyboardInterrupt:
        log.info("Interrupted by the user.")
        stop_threads(signal.SIGINT, None)
    # Any exception not catched at this point would make the scanner stall.
    # Log it and exit gracefully.
    except Exception as e:
        log.critical(FILLUP_TICKET_MSG)
        log.exception(e)
        stop_threads(signal.SIGTERM, None, 1)


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
    # Generate an unique identifier for each scanner
    if 'uuid' not in state:
        state['uuid'] = str(uuid.uuid4())

    run_speedtest(args, conf)
