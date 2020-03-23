"""Unit tests for heartbeat"""
import logging

from sbws.lib import heartbeat


def test_total_measured_percent(conf, caplog):
    hbeat = heartbeat.Heartbeat(conf.getpath('paths', 'state_fname'))

    hbeat.register_consensus_fprs(['A', 'B', 'C'])

    hbeat.register_measured_fpr('A')
    hbeat.register_measured_fpr('B')

    caplog.set_level(logging.INFO)

    assert hbeat.previous_measurement_percent == 0

    hbeat.print_heartbeat_message()

    assert hbeat.previous_measurement_percent == 67
    assert 0 == caplog.records[1].getMessage().find(
        "Measured in total 2 (67%)"
    )
    assert 0 == caplog.records[2].getMessage().find(
        "1 relays still not measured"
    )
