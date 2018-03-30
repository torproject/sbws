from configparser import (ConfigParser, ExtendedInterpolation)
import os
from sbws.globals import G_PKG_DIR


def _read_config_file(conf, fname):
    assert os.path.isfile(fname)
    with open(fname, 'rt') as fd:
        conf.read_file(fd, source=fname)
    return conf


def _get_default_config():
    conf = ConfigParser(interpolation=ExtendedInterpolation())
    fname = os.path.join(G_PKG_DIR, 'config.default.ini')
    assert os.path.isfile(fname)
    conf = _read_config_file(conf, fname)
    return conf


def _get_user_config(args, conf=None):
    if not conf:
        conf = ConfigParser(interpolation=ExtendedInterpolation())
    else:
        assert isinstance(conf, ConfigParser)
    fname = os.path.join(args.directory, 'config.ini')
    if not os.path.isfile(fname):
        return conf
    conf = _read_config_file(conf, fname)
    return conf


def get_config(args):
    conf = _get_default_config()
    conf = _get_user_config(args, conf=conf)
    return conf


def get_user_example_config():
    conf = ConfigParser(interpolation=ExtendedInterpolation())
    fname = os.path.join(G_PKG_DIR, 'config.example.ini')
    assert os.path.isfile(fname)
    conf = _read_config_file(conf, fname)
    return conf
