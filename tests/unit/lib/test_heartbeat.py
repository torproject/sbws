"""Unit tests for heartbeat"""
import logging
import pytest

from sbws.lib import heartbeat
from sbws.util.state import State


@pytest.mark.skip(reason="increment_recent_measurement_attempt() disabled")
def test_total_measured_percent(conf, caplog):
    state = State(conf["paths"]["state_fname"])
    state["recent_priority_list"] = [1, 2, 3]
    hbeat = heartbeat.Heartbeat(conf.getpath('paths', 'state_fname'))

    hbeat.register_consensus_fprs(['A', 'B', 'C'])

    hbeat.register_measured_fpr('A')
    hbeat.register_measured_fpr('B')

    caplog.set_level(logging.INFO)

    assert hbeat.previous_measurement_percent == 0

    hbeat.print_heartbeat_message()

    assert hbeat.previous_measurement_percent == 67
    assert 0 == caplog.records[0].getMessage().find("Run 3 main loops.")
    assert 0 == caplog.records[1].getMessage().find(
        "Measured in total 2 (67%)"
    )
    assert 0 == caplog.records[2].getMessage().find(
        "1 relays still not measured"
    )
