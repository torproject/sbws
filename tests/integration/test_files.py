"""
Integration tests for the files with data to be used by the bandwidth file.

"""
from sbws.lib.resultdump import load_recent_results_in_datadir
from sbws.lib.v3bwfile import V3BWFile
from sbws.util.state import State


def test_results(conf):
    results = load_recent_results_in_datadir(5, conf["paths"]["datadir"])
    for fp, values in results.items():
        count = max(
            [
                len(getattr(r, "relay_recent_measurement_attempt", []))
                for r in values
            ]
        )
        assert count == 1
        count = max(
            [len(getattr(r, "relay_in_recent_consensus", [])) for r in values]
        )
        assert count == 1
        count = max(
            [len(getattr(r, "relay_recent_priority_list", [])) for r in values]
        )
        assert count == 1


def test_state(conf):
    state = State(conf["paths"]["state_fpath"])
    assert 1 == state.count("recent_consensus")
    assert 1 == state.count("recent_priority_list")
    assert 15 == state.count("recent_priority_relay")
    assert 15 == state.count("recent_measurement_attempt")


def test_v3bwfile(conf):
    bwfile = V3BWFile.from_v1_fpath(
        conf["paths"]["v3bw_fname"].format("latest")
    )
    assert "1" == bwfile.header.recent_consensus_count
    assert "1" == bwfile.header.recent_priority_list_count
    assert "15" == bwfile.header.recent_priority_relay_count
    assert "15" == bwfile.header.recent_measurement_attempt_count
    for bwline in bwfile.bw_lines:
        assert 1 == bwline.relay_in_recent_consensus_count
        assert 1 == bwline.relay_recent_priority_list_count
        assert 1 == bwline.relay_recent_measurement_attempt_count
