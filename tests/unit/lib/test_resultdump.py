# -*- coding: utf-8 -*-
"""Unit tests for resultdump."""
from sbws.lib.resultdump import trim_results_ip_changed, Result, ResultSuccess


TIME1 = 1529232277.9028733
TIME2 = 1529232278.9028733
FP1 = 'A' * 40
FP2 = 'Z' * 40
ED25519 = 'g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s'
CIRC = [FP1, FP2]
DEST_URL = 'http://example.com/sbws.bin'
NICK = 'A'
RELAY_IP1 = '169.254.100.1'
RELAY_IP2 = '169.254.100.2'
RELAY1 = Result.Relay(FP1, NICK, RELAY_IP1, ED25519)
RELAY2 = Result.Relay(FP1, NICK, RELAY_IP2, ED25519)
RTTS = [5, 25]
DOWNLOADS = [{'duration': 4, 'amount': 40}]

RESULTSUCCESS1 = ResultSuccess(RTTS, DOWNLOADS, RELAY1, CIRC, DEST_URL,
                               'sbws', t=TIME1)
RESULTSUCCESS2 = ResultSuccess(RTTS, DOWNLOADS, RELAY2, CIRC, DEST_URL,
                               'sbws', t=TIME2)
RESULTDICT_IP_CHANGED = {FP1: [RESULTSUCCESS1, RESULTSUCCESS2]}
RESULTDICT_IP_NOT_CHANGED = {FP1: [RESULTSUCCESS1, RESULTSUCCESS1]}


def test_trim_results_ip_changed():
    expected_results_dict = {FP1: [RESULTSUCCESS2]}
    results_dict = trim_results_ip_changed(RESULTDICT_IP_CHANGED)
    assert expected_results_dict == results_dict


def test_trim_results_ip_changed_false():
    results_dict = trim_results_ip_changed(RESULTDICT_IP_CHANGED)
    assert RESULTDICT_IP_NOT_CHANGED == results_dict
