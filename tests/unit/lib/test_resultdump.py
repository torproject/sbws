# -*- coding: utf-8 -*-
"""Unit tests for resultdump."""
from sbws.lib.resultdump import trim_results_ip_changed


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
