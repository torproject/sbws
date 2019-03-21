"""Unit tests for heartbeat"""
import logging
import time

from sbws.lib import heartbeat

def test_total_measured_percent(conf, caplog):
    heartbeat = heartbeat.Heartbeat(conf.getpath('paths', 'state_fname'))

    heartbeat.register_consensus_fpr(['A', 'B', 'C'])

    haertbeat.register_measured_fpr('A')
    haertbeat.register_measured_fpr('B')

    caplog.set_level(logging.INFO)

    heartbeat.print_heartbeat_message()

    assert heartbeat.previous_measured_percent == 67
    caplog.records[1].getMessage().find("Measured in total 2 (67%)")
    caplog.records[2].getMessage().find("1 relays still not measured")
