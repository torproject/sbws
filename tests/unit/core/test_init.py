"""Unit tests for sbws.core.init."""
import logging
import os.path

import sbws


def test_sbwshome_only_datadir(sbwshome_only_datadir, args, conf, caplog):
    caplog.set_level(logging.DEBUG)
    sbws.core.init.main(args, conf)
    print(caplog.records[-1].getMessage())
    assert "Creating {} based on example config".format(
        os.path.join(conf['paths']['sbws_home'], 'config.ini')) \
        in caplog.records[-1].getMessage()
    assert os.path.isdir(conf['paths']['sbws_home'])
    assert os.path.isdir(conf['paths']['datadir'])
    assert os.path.isfile(os.path.join(conf['paths']['sbws_home'],
                          'config.ini'))


def test_sbwshome_empty(args, conf, caplog):
    caplog.set_level(logging.DEBUG)
    sbws.core.init.main(args, conf)
    assert "Creating {} based on example config".format(
        os.path.join(conf['paths']['sbws_home'], 'config.ini')) \
        in caplog.records[-1].getMessage()
    assert os.path.isdir(conf['paths']['sbws_home'])
    assert os.path.isfile(os.path.join(conf['paths']['sbws_home'],
                          'config.ini'))


def test_sbwshome(sbwshome, args, conf, caplog):
    caplog.set_level(logging.DEBUG)
    try:
        sbws.core.init.main(args, conf)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert None, 'Should have failed'
    assert "Directory already seems to be initted" \
        in caplog.records[-1].getMessage()
    assert os.path.isdir(conf['paths']['sbws_home'])
    assert os.path.isdir(conf['paths']['datadir'])
    assert os.path.isfile(os.path.join(conf['paths']['sbws_home'],
                          'config.ini'))
