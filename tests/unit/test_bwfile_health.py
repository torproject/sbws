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
