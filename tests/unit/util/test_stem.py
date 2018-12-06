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


def test_parse_user_torrc_config_existing_keyvalue_options_fail(caplog):
    torrc_dict = {'SocksPort': 'auto'}
    config_torrc_extra_lines = """
    SocksPort 9050
    """
    torrc_dict_new = parse_user_torrc_config(
        torrc_dict, config_torrc_extra_lines)

    # the new dictionary contains the existing option
    assert torrc_dict_new == torrc_dict

    # but it does not contain the new option
    assert config_torrc_extra_lines.strip() in caplog.records[-1].getMessage()
