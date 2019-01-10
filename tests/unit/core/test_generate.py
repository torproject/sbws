"""Unit tests for sbws.core.generate module."""
import argparse

from sbws.core.generate import gen_parser
from sbws.globals import PROP276_ROUND_DIG, TORFLOW_ROUND_DIG


def test_gen_parser_arg_round_digs():
    """
    Test that both --torflow-round-digs and --round-digs arguments can be
    passed and round-digs is PROP276_ROUND_DIG by default.

    """
    parent_parser = argparse.ArgumentParser(prog='sbws')
    subparsers = parent_parser.add_subparsers(help='generate help')
    parser_generate = gen_parser(subparsers)
    # Explicitely set empty arguments, otherwise pytest will use pytest
    # arguments
    args = parser_generate.parse_args([])
    assert args.round_digs == PROP276_ROUND_DIG
    # torflow_round_digs is not in the Namespace
    assert getattr(args, 'torflow_round_digs', None) is None
    # but it can still be passed as an argument
    args = parser_generate.parse_args(['--torflow-round-digs',
                                       str(TORFLOW_ROUND_DIG)])
    # though the variable is named round_digs
    assert args.round_digs == TORFLOW_ROUND_DIG
    # or use the short version
    args = parser_generate.parse_args(['-r', str(TORFLOW_ROUND_DIG)])
    assert args.round_digs == TORFLOW_ROUND_DIG
    # or use round-digs explicitely
    args = parser_generate.parse_args(['--round-digs',
                                       str(PROP276_ROUND_DIG)])
    assert args.round_digs == PROP276_ROUND_DIG
