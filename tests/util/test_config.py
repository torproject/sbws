import sbws.util.config as con
from configparser import ConfigParser


class Section:
    def __init__(self, key, value, mini=None, maxi=None):
        self.key = key
        self.value = value
        self.mini = mini
        self.maxi = maxi

    def getfloat(self, key):
        assert key == self.key, 'But in tests; key should exist'
        return float(self.value)

    def getint(self, key):
        assert key == self.key, 'But in tests; key should exist'
        return int(self.value)


def test_validate_fingerprint():
    fp_len = 40
    bads = [
        'A' * (fp_len - 1), 'A' * (fp_len + 1),
        '', 'A' * (1000000),
        'a' * fp_len, 'O' * fp_len
    ]
    goods = [
        'A' * fp_len,
        ''.join(list('0123456789ABCDEF' * 3)[0:fp_len])
    ]
    for fp in bads:
        d = {'': fp}
        valid, reason = con._validate_fingerprint(d, '')
        assert not valid, 'Fingerprint {} should not have passed '\
            'validation'.format(fp)
    for fp in goods:
        d = {'': fp}
        valid, reason = con._validate_fingerprint(d, '')
        assert valid, 'Fingerprint {} should have passed, but didn\'t '\
            'because {}'.format(fp, reason)


def test_validate_int_simple():
    bads = [
        Section('', 'NotAInt'),
        Section('', '-0.1'), Section('', '0.1'),
    ]
    goods = [
        Section('', '0'), Section('', '1'), Section('', '-1'),
        Section('', '100000000'), Section('', '-1000000000'),
        Section('', '+0'), Section('', '-0'),
    ]
    for sec in bads:
        valid, reason = con._validate_int(sec, sec.key)
        assert not valid, '{} should not have been a valid '\
            'int'.format(sec.value)
    for sec in goods:
        valid, reason = con._validate_int(sec, sec.key)
        assert valid, '{} should have been a valid int, but '\
            'got: {}'.format(sec.value, reason)


def test_validate_float_simple():
    bads = [
        Section('', 'NotAFloat'),
    ]
    goods = [
        Section('', '0'), Section('', '1'), Section('', '-1'),
        Section('', '-0.1'), Section('', '0.1'),
        Section('', '100000000'), Section('', '-1000000000'),
        Section('', '+0'), Section('', '-0'),
    ]
    for sec in bads:
        valid, reason = con._validate_float(sec, sec.key)
        assert not valid, '{} should not have been a valid '\
            'float'.format(sec.value)
    for sec in goods:
        valid, reason = con._validate_float(sec, sec.key)
        assert valid, '{} should have been a valid float, but '\
            'got: {}'.format(sec.value, reason)


def test_validate_int_min():
    goods = [
        Section('', '0', mini=0),
        Section('', '1', mini=1), Section('', '-1', mini=-1),
    ]
    bads = [
        Section('', '1', mini=2),
        Section('', '0', mini=1),
    ]
    for sec in bads:
        valid, reason = con._validate_int(sec, sec.key, minimum=sec.mini)
        assert not valid, '{} should not have been a valid '\
            'int'.format(sec.value)
    for sec in goods:
        valid, reason = con._validate_int(sec, sec.key, minimum=sec.mini)
        assert valid, '{} should have been a valid int, but '\
            'got: {}'.format(sec.value, reason)


def test_validate_float_min():
    goods = [
        Section('', '0', mini=0.0),
        Section('', '0.1', mini=0.1), Section('', '-0.1', mini=-0.1),
        Section('', '0.1', mini=-0.1),
    ]
    bads = [
        Section('', '0.0999999999', mini=0.1),
    ]
    for sec in bads:
        valid, reason = con._validate_float(sec, sec.key, minimum=sec.mini)
        assert not valid, '{} should not have been a valid '\
            'float'.format(sec.value)
    for sec in goods:
        valid, reason = con._validate_float(sec, sec.key, minimum=sec.mini)
        assert valid, '{} should have been a valid float, but '\
            'got: {}'.format(sec.value, reason)


def test_validate_int_max():
    goods = [
        Section('', '0', maxi=0),
        Section('', '1', maxi=1), Section('', '-1', maxi=-1),
        Section('', '-1', maxi=1),
    ]
    bads = [
        Section('', '2', maxi=1),
        Section('', '1', maxi=0),
    ]
    for sec in bads:
        valid, reason = con._validate_int(sec, sec.key, maximum=sec.maxi)
        assert not valid, '{} should not have been a valid '\
            'int'.format(sec.value)
    for sec in goods:
        valid, reason = con._validate_int(sec, sec.key, maximum=sec.maxi)
        assert valid, '{} should have been a valid int, but '\
            'got: {}'.format(sec.value, reason)


def test_validate_float_max():
    goods = [
        Section('', '0', maxi=0.0),
        Section('', '0.1', maxi=0.1), Section('', '-0.1', maxi=-0.1),
        Section('', '-0.1', maxi=0.1),
    ]
    bads = [
        Section('', '0.10000000001', maxi=0.1),
    ]
    for sec in bads:
        valid, reason = con._validate_float(sec, sec.key, maximum=sec.maxi)
        assert not valid, '{} should not have been a valid '\
            'float'.format(sec.value)
    for sec in goods:
        valid, reason = con._validate_float(sec, sec.key, maximum=sec.maxi)
        assert valid, '{} should have been a valid float, but '\
            'got: {}'.format(sec.value, reason)


def test_validate_bool():
    goods = [
        'on', 'True', 'true', 'yes',
        'off', 'False', 'false', 'no',
        '0', '1',
    ]
    bads = [
        'onn', 'offf',
        '2', '',
    ]
    for val in goods:
        conf = ConfigParser()
        conf.read_dict({'sec': {}})
        conf['sec']['key'] = val
        valid, reason = con._validate_boolean(conf['sec'], 'key')
        assert valid, '{} should have been a valid bool, but '\
            'got: {}'.format(val, reason)
    for val in bads:
        conf = ConfigParser()
        conf.read_dict({'sec': {}})
        conf['sec']['key'] = val
        valid, reason = con._validate_boolean(conf['sec'], 'key')
        assert not valid, '{} should not have been a valid '\
            'bool'.format(val)
