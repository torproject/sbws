from configparser import (ConfigParser, ExtendedInterpolation)
import os
import logging
import logging.config
from string import Template
from tempfile import NamedTemporaryFile
from sbws.globals import G_PKG_DIR

_ALPHANUM = 'abcdefghijklmnopqrstuvwxyz'
_ALPHANUM += _ALPHANUM.upper()
_ALPHANUM += '0123456789'

_HEX = '0123456789ABCDEF'

log = logging.getLogger(__name__)


def _read_config_file(conf, fname):
    assert os.path.isfile(fname)
    log.debug('Reading config file %s', fname)
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


def _get_user_logging_config(args, conf=None):
    if not conf:
        conf = ConfigParser(interpolation=ExtendedInterpolation())
    else:
        assert isinstance(conf, ConfigParser)
    fname = os.path.join(args.directory, 'config.log.ini')
    if not os.path.isfile(fname):
        return conf
    conf = _read_config_file(conf, fname)
    return conf


def _get_default_logging_config(args, conf=None):
    if not conf:
        conf = ConfigParser(interpolation=ExtendedInterpolation())
    else:
        assert isinstance(conf, ConfigParser)
    fname = os.path.join(G_PKG_DIR, 'config.log.default.ini')
    assert os.path.isfile(fname)
    conf = _read_config_file(conf, fname)
    return conf


def get_config(args):
    conf = _get_default_config()
    conf = _get_default_logging_config(args, conf=conf)
    conf = _get_user_config(args, conf=conf)
    conf = _get_user_logging_config(args, conf=conf)
    return conf


def get_user_example_config():
    conf = ConfigParser(interpolation=ExtendedInterpolation())
    fname = os.path.join(G_PKG_DIR, 'config.example.ini')
    assert os.path.isfile(fname)
    conf = _read_config_file(conf, fname)
    return conf


def configure_logging(conf):
    assert isinstance(conf, ConfigParser)
    with NamedTemporaryFile('w+t') as fd:
        conf.write(fd)
        fd.seek(0, 0)
        logging.config.fileConfig(fd.name)


def validate_config(conf):
    ''' Checks the given conf for bad values or bad combinations of values. If
    there's something wrong, returns False and a list of error messages.
    Otherwise, return True and an empty list '''
    errors = []
    errors.extend(_validate_general(conf))
    errors.extend(_validate_cleanup(conf))
    errors.extend(_validate_client(conf))
    errors.extend(_validate_server(conf))
    errors.extend(_validate_server_passwords(conf))
    errors.extend(_validate_tor(conf))
    errors.extend(_validate_paths(conf))
    errors.extend(_validate_helpers(conf))
    return len(errors) < 1, errors


def _validate_cleanup(conf):
    errors = []
    sec = 'cleanup'
    err_tmpl = Template('$sec/$key ($val): $e')
    ints = {
        'stale_days': {'minimum': 1, 'maximum': None},
        'rotten_days': {'minimum': 1, 'maximum': None},
    }
    all_valid_keys = list(ints.keys())
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl))
    errors.extend(_validate_section_ints(conf, sec, ints, err_tmpl))
    return errors


def _validate_general(conf):
    errors = []
    sec = 'general'
    err_tmpl = Template('$sec/$key ($val): $e')
    ints = {
        'data_period': {'minimum': 1, 'maximum': None},
    }
    all_valid_keys = list(ints.keys())
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl))
    errors.extend(_validate_section_ints(conf, sec, ints, err_tmpl))
    return errors


def _validate_paths(conf):
    errors = []
    sec = 'paths'
    err_tmpl = Template('$sec/$key ($val): $e')
    unvalidated_keys = ['passwords', 'datadir', 'sbws_home']
    all_valid_keys = unvalidated_keys
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl))
    return errors


def _validate_client(conf):
    errors = []
    sec = 'client'
    err_tmpl = Template('$sec/$key ($val): $e')
    ints = {
        'max_recv_per_read': {'minimum': 1, 'maximum': None},
        'num_rtts': {'minimum': 1, 'maximum': 100},
        'num_downloads': {'minimum': 1, 'maximum': 100},
        'initial_read_request': {'minimum': 1, 'maximum': None},
        'measurement_threads': {'minimum': 1, 'maximum': None},
    }
    floats = {
        'download_toofast': {'minimum': 0.001, 'maximum': None},
        'download_min': {'minimum': 0.001, 'maximum': None},
        'download_target': {'minimum': 0.001, 'maximum': None},
        'download_max': {'minimum': 0.001, 'maximum': None},
    }
    hosts = {
        'tor_socks_host': {},
    }
    ports = {
        'tor_socks_port': {},
    }
    bools = {
        'measure_authorities': {},
    }
    all_valid_keys = list(ints.keys()) + list(floats.keys()) + \
        list(hosts.keys()) + list(ports.keys()) + list(bools.keys()) + \
        ['nickname']
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl))
    errors.extend(_validate_section_ints(conf, sec, ints, err_tmpl))
    errors.extend(_validate_section_floats(conf, sec, floats, err_tmpl))
    # XXX: validate hosts func doesn't do anything currently
    errors.extend(_validate_section_hosts(conf, sec, hosts, err_tmpl))
    errors.extend(_validate_section_ports(conf, sec, ports, err_tmpl))
    errors.extend(_validate_section_bools(conf, sec, bools, err_tmpl))
    valid, error_msg = _validate_nickname(conf[sec], 'nickname')
    if not valid:
        errors.append(err_tmpl.substitute(
            sec=sec, key='nickname', val=conf[sec]['nickname'], e=error_msg))
    return errors


def _validate_server(conf):
    errors = []
    sec = 'server'
    err_tmpl = Template('$sec/$key ($val): $e')
    ints = {
        'max_send_per_write': {'minimum': 1, 'maximum': None},
    }
    hosts = {
        'bind_ip': {},
    }
    ports = {
        'bind_port': {},
    }
    all_valid_keys = list(ints.keys()) + list(hosts.keys()) + \
        list(ports.keys())
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl))
    errors.extend(_validate_section_ints(conf, sec, ints, err_tmpl))
    # XXX: validate hosts func doesn't do anything currently
    errors.extend(_validate_section_hosts(conf, sec, hosts, err_tmpl))
    errors.extend(_validate_section_ports(conf, sec, ports, err_tmpl))
    return errors


def _validate_server_passwords(conf):
    errors = []
    sec = 'server.passwords'
    err_tmpl = Template('$sec/$key ($val): $e')
    section = conf[sec]
    for key in section.keys():
        valid, error_msg = _validate_password(section, key)
        if not valid:
            errors.append(err_tmpl.substitute(
                sec=sec, key=key, val=section[key], e=error_msg))
    return errors


def _validate_tor(conf):
    errors = []
    sec = 'tor'
    err_tmpl = Template('$sec/$key ($val): $e')
    enums = {
        'control_type': {'valid': ['port', 'socket']},
    }
    unvalidated_keys = ['control_location']
    all_valid_keys = list(enums.keys()) + unvalidated_keys
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl))
    errors.extend(_validate_section_enums(conf, sec, enums, err_tmpl))
    return errors


def _validate_helpers(conf):
    errors = []
    sec = 'helpers'
    section = conf[sec]
    err_tmpl = Template('$sec/$key ($val): $e')
    addtional_helper_sections = []
    for key in section.keys():
        valid, error_msg = _validate_boolean(section, key)
        value = section[key]
        if not valid:
            errors.append(err_tmpl.substitute(
                sec=sec, key=key, val=value, e=error_msg))
            continue
        assert valid
        if section.getboolean(key):
            addtional_helper_sections.append('{}.{}'.format(sec, key))
    fps = {
        'relay': {},
    }
    hosts = {
        'server_host': {},
    }
    ports = {
        'server_port': {},
    }
    passwords = {
        'password': {},
    }
    all_valid_keys = list(fps.keys()) + list(hosts.keys()) + \
        list(ports.keys()) + list(passwords.keys())
    for sec in addtional_helper_sections:
        if sec not in conf:
            errors.append('{} is an enabled helper but is not a section in '
                          'the config'.format(sec))
            continue
        errors.extend(_validate_section_keys(conf, sec, all_valid_keys,
                                             err_tmpl))
        errors.extend(_validate_section_fingerprints(conf, sec, fps, err_tmpl))
        errors.extend(_validate_section_hosts(conf, sec, hosts, err_tmpl))
        errors.extend(_validate_section_ports(conf, sec, ports, err_tmpl))
        errors.extend(_validate_section_passwords(conf, sec, passwords,
                                                  err_tmpl))
    return errors


def _validate_section_keys(conf, sec, keys, tmpl):
    errors = []
    section = conf[sec]
    for key in section:
        if key not in keys:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key], e='Unknown key'))
    return errors


def _validate_section_enums(conf, sec, enums, tmpl):
    errors = []
    section = conf[sec]
    for key in enums:
        valid = enums[key]['valid']
        if section[key] not in valid:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key],
                e='Must be one of {}'.format(valid)))
    return errors


def _validate_section_ints(conf, sec, ints, tmpl):
    errors = []
    section = conf[sec]
    for key in ints:
        valid, error = _validate_int(
            section, key, minimum=ints[key]['minimum'],
            maximum=ints[key]['maximum'])
        if not valid:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key], e=error))
    return errors


def _validate_section_floats(conf, sec, floats, tmpl):
    errors = []
    section = conf[sec]
    for key in floats:
        valid, error = _validate_float(
            section, key, minimum=floats[key]['minimum'],
            maximum=floats[key]['maximum'])
        if not valid:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key], e=error))
    return errors


def _validate_section_hosts(conf, sec, hosts, tmpl):
    errors = []
    section = conf[sec]
    for key in hosts:
        valid, error = _validate_host(section, key)
        if not valid:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key], e=error))
    return errors


def _validate_section_ports(conf, sec, ports, tmpl):
    errors = []
    section = conf[sec]
    for key in ports:
        valid, error = _validate_int(section, key, minimum=1, maximum=2**16)
        if not valid:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key],
                e='Not a valid port ({})'.format(error)))
    return errors


def _validate_section_bools(conf, sec, bools, tmpl):
    errors = []
    section = conf[sec]
    for key in bools:
        valid, error = _validate_boolean(section, key)
        if not valid:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key],
                e='Not a valid boolean string ({})'.format(error)))
    return errors


def _validate_section_fingerprints(conf, sec, fps, tmpl):
    errors = []
    section = conf[sec]
    for key in fps:
        valid, error = _validate_fingerprint(section, key)
        if not valid:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key],
                e='Not a valid fingerprint ({})'.format(error)))
    return errors


def _validate_section_passwords(conf, sec, passwords, tmpl):
    errors = []
    section = conf[sec]
    for key in passwords:
        valid, error = _validate_password(section, key)
        if not valid:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key],
                e='Not a valid password ({})'.format(error)))
    return errors


def _validate_int(section, key, minimum=None, maximum=None):
    try:
        value = section.getint(key)
    except ValueError as e:
        return False, e
    if minimum is not None:
        assert isinstance(minimum, int)
        if value < minimum:
            return False, 'Cannot be less than {}'.format(minimum)
    if maximum is not None:
        assert isinstance(maximum, int)
        if value > maximum:
            return False, 'Cannot be greater than {}'.format(maximum)
    return True, ''


def _validate_boolean(section, key):
    try:
        section.getboolean(key)
    except ValueError as e:
        return False, e
    return True, ''


def _validate_float(section, key, minimum=None, maximum=None):
    try:
        value = section.getfloat(key)
    except ValueError as e:
        return False, e
    if minimum is not None:
        assert isinstance(minimum, float)
        if value < minimum:
            return False, 'Cannot be less than {}'.format(minimum)
    if maximum is not None:
        assert isinstance(maximum, float)
        if value > maximum:
            return False, 'Cannot be greater than {}'.format(maximum)
    return True, ''


def _validate_host(section, key):
    # XXX: Implement this
    return True, ''


def _validate_fingerprint(section, key):
    alphabet = _HEX
    length = 40
    return _validate_string(section, key, min_len=length, max_len=length,
                            alphabet=alphabet)


def _validate_password(section, key):
    alphabet = _ALPHANUM
    length = 64
    return _validate_string(section, key, min_len=length, max_len=length,
                            alphabet=alphabet)


def _validate_nickname(section, key):
    alphabet = _ALPHANUM
    min_len = 1
    max_len = 32
    return _validate_string(section, key, min_len=min_len, max_len=max_len,
                            alphabet=alphabet)


def _validate_string(section, key, min_len=None, max_len=None, alphabet=None):
    s = section[key]
    if min_len is not None and len(s) < min_len:
        return False, '{} is below minimum allowed length {}'.format(
            len(s), min_len)
    if max_len is not None and len(s) > max_len:
        return False, '{} is above maximum allowed length {}'.format(
            len(s), max_len)
    if alphabet is not None:
        for i, c in enumerate(s):
            if c not in alphabet:
                return False, 'Letter {} at position {} is not in allowed '\
                    'characters "{}"'.format(c, i, alphabet)
    return True, ''
