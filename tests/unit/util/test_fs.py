"""Unit tests for fs module"""
from unittest.mock import patch

from sbws.util import fs


def mock_df_zero(path):
    return 0


def mock_df_enough(path):
    return 32


@patch('sbws.util.fs.df', mock_df_zero)
def test_is_low_space_true(caplog, conf):
    assert fs.is_low_space(conf) is True
    assert ' is less than ' in caplog.records[-1].getMessage()


@patch('sbws.util.fs.df', mock_df_enough)
def test_is_low_space_false(conf):
    assert fs.is_low_space(conf) is False
