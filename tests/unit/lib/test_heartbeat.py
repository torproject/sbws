"""Unit tests for heartbeat"""
import logging
import time

from sbws.lib import heartbeat


def test_total_measured_percent(conf, caplog):
    measured_percent = 0
    measured_fp_set = set(['A', 'B'])
    main_loop_tstart = time.monotonic()
    relays_fingerprints = set(['A', 'B', 'C'])

    caplog.set_level(logging.INFO)
    new_measured_percent = heartbeat.total_measured_percent(
            measured_percent, relays_fingerprints, measured_fp_set,
            main_loop_tstart, conf.getpath('paths', 'state_fname')
            )
    assert new_measured_percent == 67
    caplog.records[1].getMessage().find("Measured in total 2 (67%)")
    caplog.records[2].getMessage().find("1 relays still not measured")
