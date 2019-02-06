import sbws.util.config as con
from configparser import ConfigParser


class PseudoSection:
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
        PseudoSection('', 'NotAInt'),
        PseudoSection('', '-0.1'), PseudoSection('', '0.1'),
    ]
    goods = [
        PseudoSection('', '0'),
        PseudoSection('', '1'), PseudoSection('', '-1'),
        PseudoSection('', '100000000'), PseudoSection('', '-1000000000'),
        PseudoSection('', '+0'), PseudoSection('', '-0'),
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
        PseudoSection('', 'NotAFloat'),
    ]
    goods = [
        PseudoSection('', '0'),
        PseudoSection('', '1'), PseudoSection('', '-1'),
        PseudoSection('', '-0.1'), PseudoSection('', '0.1'),
        PseudoSection('', '100000000'), PseudoSection('', '-1000000000'),
        PseudoSection('', '+0'), PseudoSection('', '-0'),
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
        PseudoSection('', '0', mini=0),
        PseudoSection('', '1', mini=1), PseudoSection('', '-1', mini=-1),
    ]
    bads = [
        PseudoSection('', '1', mini=2),
        PseudoSection('', '0', mini=1),
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
        PseudoSection('', '0', mini=0.0),
        PseudoSection('', '0.1', mini=0.1),
        PseudoSection('', '-0.1', mini=-0.1),
        PseudoSection('', '0.1', mini=-0.1),
    ]
    bads = [
        PseudoSection('', '0.0999999999', mini=0.1),
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
        PseudoSection('', '0', maxi=0),
        PseudoSection('', '1', maxi=1), PseudoSection('', '-1', maxi=-1),
        PseudoSection('', '-1', maxi=1),
    ]
    bads = [
        PseudoSection('', '2', maxi=1),
        PseudoSection('', '1', maxi=0),
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
        PseudoSection('', '0', maxi=0.0),
        PseudoSection('', '0.1', maxi=0.1),
        PseudoSection('', '-0.1', maxi=-0.1),
        PseudoSection('', '-0.1', maxi=0.1),
    ]
    bads = [
        PseudoSection('', '0.10000000001', maxi=0.1),
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


def test_validate_url():
    goods = [
        'https://example.com', 'https://example.com/',
        'https://example.com/foo.bar',
        'https://example.com/foo/bar',
        'https://user@example.com',
        'https://48.290.983.123:4443',
        'http://127.0.0.1:8000'
    ]
    bads = [
        'ftp://example.com/foo.bar',
        'http://', 'http:///',
        'http://example.com',
    ]
    for val in goods:
        d = {'': val}
        valid, reason = con._validate_url(d, '')
        assert valid, '{} should have been a valid URL, but '\
            'got: {}'.format(val, reason)
    for val in bads:
        d = {'': val}
        valid, reason = con._validate_url(d, '')
        assert not valid, '{} should not have been a valid URL'.format(val)


def test_nickname():
    max_len = 32
    goods = [
        'aaa', 'AAA', 'aAa', 'A1a', '1aA', 'aA1',
        '!!!', '!@#',
        'a!A', '!Aa', 'Aa!',
        'a' * max_len,
    ]
    bads = [
        '', 'a' * (max_len + 1),
        '"', '\'',
    ]
    for nick in goods:
        d = {'n': nick}
        valid, reason = con._validate_nickname(d, 'n')
        assert valid, reason
    for nick in bads:
        d = {'n': nick}
        valid, reason = con._validate_nickname(d, 'n')
        assert not valid, reason


def test_country(conf):
    from string import Template
    err_tmpl = Template('$sec/$key ($val): $e')

    # Invalid default country code in scanner section
    errors = con._validate_country(conf, 'scanner', 'country', err_tmpl)
    assert errors[0] == \
        'scanner/country (AA): Not a valid ISO 3166 alpha-2 country code.'

    # Valid country code in scanner section
    conf['scanner']['country'] = 'US'
    errors = con._validate_country(conf, 'scanner', 'country', err_tmpl)
    assert not errors

    # No country in destinations.foo section
    conf['destinations']['foo'] = 'on'
    conf['destinations.foo'] = {}
    conf['destinations.foo']['url'] = 'https://foo.bar'
    errors = con._validate_country(
        conf, 'destinations.foo', 'country', err_tmpl)
    assert errors[0] == \
        'destinations.foo/country (None): ' \
        'Missing country in configuration file.'

    # Valid country in destinations.foo section
    conf['destinations.foo']['url'] = 'US'
    errors = con._validate_country(conf, 'scanner', 'country', err_tmpl)
    assert not errors


def test_config_arg_provided_but_no_found(args, conf):
    args.config = 'non_existing_file'
    user_conf = con._get_user_config(args, conf)
    # since the user configuration is not found, it is the same as conf
    assert conf.__dict__.items() == user_conf.__dict__.items()


def test_config_arg_provided(args, conf, datadir):
    args.config = datadir.join('user_sbws.ini')
    user_conf = con._get_user_config(args, conf)
    assert user_conf['paths']['sbws_home'] == '/tmp/.sbws'
