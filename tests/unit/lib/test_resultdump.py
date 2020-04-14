# -*- coding: utf-8 -*-
"""Unit tests for resultdump."""

import datetime

from sbws.lib.relaylist import Relay
from sbws.lib.resultdump import (
    ResultError,
    ResultErrorStream,
    ResultSuccess,
    trim_results_ip_changed,
    load_result_file
)


def test_trim_results_ip_changed_defaults(resultdict_ip_not_changed):
    results_dict = trim_results_ip_changed(resultdict_ip_not_changed)
    assert resultdict_ip_not_changed == results_dict


def test_trim_results_ip_changed_on_changed_ipv4_changed(
        resultdict_ip_changed, resultdict_ip_changed_trimmed):
    results_dict = trim_results_ip_changed(resultdict_ip_changed,
                                           on_changed_ipv4=True)
    assert resultdict_ip_changed_trimmed == results_dict


def test_trim_results_ip_changed_on_changed_ipv4_no_changed(
        resultdict_ip_not_changed):
    results_dict = trim_results_ip_changed(resultdict_ip_not_changed,
                                           on_changed_ipv4=True)
    assert resultdict_ip_not_changed == results_dict


def test_trim_results_ip_changed_on_changed_ipv6(caplog,
                                                 resultdict_ip_not_changed):
    results_dict = trim_results_ip_changed(resultdict_ip_not_changed,
                                           on_changed_ipv6=True)
    assert resultdict_ip_not_changed == results_dict
    for record in caplog.records:
        assert record.levelname == 'WARNING'
    assert 'Reseting bandwidth results when IPv6 changes, ' \
           'is not yet implemented.\n' in caplog.text


def test_resultdump(
    rd, args, conf_results, controller, router_status, server_descriptor
):
    from sbws import settings
    relay = Relay(
        router_status.fingerprint,
        controller,
        ns=router_status,
        desc=server_descriptor,
    )
    relay.increment_relay_recent_priority_list()
    relay.increment_relay_recent_measurement_attempt()
    r = ResultSuccess(
        [], 2000, relay, ["A", "B"], "http://localhost/bw", "scanner_nick",
    )
    # Storing the result with `rd.queue.put` will not store the result to disk
    # because the thread is not spawned with pytest.
    rd.store_result(r)
    results = rd.results_for_relay(relay)
    # It has stored the result
    assert 1 == len(results)
    # The result has the correct attribute
    assert 1 == len(results[0].relay_recent_priority_list)
    # Store a second result for the sme relay
    r = ResultError(
        relay, ["A", "B"], "http://localhost/bw", "scanner_nick",
    )
    rd.store_result(r)
    assert 2 == len(results)
    assert 1 == len(results[1].relay_recent_priority_list)
    settings.set_end_event()


def test_load(datadir):
    results = load_result_file(str(datadir.join("results.txt")))
    results = [v for values in results.values() for v in values]
    r1 = results[1]
    assert isinstance(r1, ResultSuccess)
    assert isinstance(
        r1.relay_recent_measurement_attempt[0], datetime.datetime
    )
    assert 2 == len(r1.relay_recent_measurement_attempt)
    assert 3 == len(r1.relay_recent_priority_list)
    assert 3 == len(r1.relay_in_recent_consensus)
    r2 = results[2]
    assert isinstance(r2, ResultErrorStream)
    assert isinstance(
        r2.relay_recent_measurement_attempt[0], datetime.datetime
    )
    assert 2 == len(r2.relay_recent_measurement_attempt)
    assert 3 == len(r2.relay_recent_priority_list)
    assert 3 == len(r2.relay_in_recent_consensus)
