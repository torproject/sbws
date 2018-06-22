import pytest
from tempfile import TemporaryDirectory
from sbws.util.parser import create_parser
from sbws.util.config import get_config
from sbws.util.stem import launch_tor
import sbws.core.init
import os


@pytest.fixture(scope='session')
def parser():
    return create_parser()


@pytest.fixture(scope='session')
def persistent_empty_dotsbws(parser):
    '''
    Creates a ~/.sbws with nothing in it but a config.ini and a datadir/
    '''
    d = TemporaryDirectory()
    args = parser.parse_args(
        '-d {} --log-level DEBUG init'.format(d.name).split())
    conf = get_config(args)
    sbws.core.init.main(args, conf)
    os.makedirs(os.path.join(d.name, 'datadir'))
    return d


@pytest.fixture(scope='session')
def persistent_launch_tor(parser, persistent_empty_dotsbws):
    d = persistent_empty_dotsbws
    args = parser.parse_args('-d {}'.format(d.name).split())
    conf = get_config(args)
    conf['tor']['extra_lines'] = '''  # noqa: E501
DirAuthority auth1 orport=2002 no-v2 v3ident=D7DBC517EFD2BA1A5012CF1BD0BB38F17C8160BD 127.10.0.1:2003 AA45C13025C037F056E734169891878ED0880231
DirAuthority auth2 orport=2002 no-v2 v3ident=4EE103A081F400E6622F5461D51782B876BB5C24 127.10.0.2:2003 E7B3C9A0040D628DAC88B0251AE6334D28E8F531
DirAuthority auth3 orport=2002 no-v2 v3ident=8B85069C7FC0593801E6491A34100264FCE28980 127.10.0.3:2003 35E3B8BB71C81355649AEC5862ECB7ED7EFDBC5C
TestingTorNetwork 1
NumCPUs 1
LogTimeGranularity 1
SafeLogging 0
'''
    cont = launch_tor(conf)
    return cont
