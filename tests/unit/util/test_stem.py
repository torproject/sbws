"""Unit tests for stem.py"""

from sbws.util.stem import parse_user_torrc_config


def test_parse_user_torrc_config_new_keyvalue_options_success():
    config_torrc_extra_lines = """
    Log debug file /tmp/tor-debug.log
    NumCPUs 1
    """
    torrc_dict = parse_user_torrc_config({}, config_torrc_extra_lines)
    assert torrc_dict == \
        {'Log': 'debug file /tmp/tor-debug.log', 'NumCPUs': '1'}
