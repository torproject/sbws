"""Test that the KeyValues in a bandwidth file make sense."""
import os.path

from sbws.lib.bwfile_health import BwFile


def test_bwfile_health(root_data_path):
    bwfile = BwFile.load(os.path.join(
        root_data_path, "2020-03-22-08-35-00-bandwidth"
    ))
    assert bwfile.header.is_correct
    assert bwfile.are_bwlines_correct
    assert bwfile.is_correct


def test_bwlines_health(capsys, root_data_path):
    bwfile = BwFile.load(os.path.join(
        root_data_path, "2020-03-22-08-35-00-bandwidth"
    ))
    out = (
        "\nrelay_recent_measurement_attempt_count <= relay_recent_priority_list_count,\n"  #noqa
        "True\n"
        "relay_recent_priority_list_count <= relay_recent_consensus_count,\n"
        "True\n\n"
    )
    for bwline in bwfile.bwlines:
        bwline.report
        assert out == capsys.readouterr().out
