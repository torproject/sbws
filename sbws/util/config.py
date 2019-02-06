"""Util functions to manage sbws configuration files."""

from configparser import (ConfigParser, ExtendedInterpolation)
from configparser import InterpolationMissingOptionError
import os
import logging
import logging.config
from urllib.parse import urlparse
from string import Template
from tempfile import NamedTemporaryFile
from sbws.globals import (DEFAULT_CONFIG_PATH, DEFAULT_LOG_CONFIG_PATH,
                          USER_CONFIG_PATH, SUPERVISED_RUN_DPATH,
                          SUPERVISED_USER_CONFIG_PATH)

from sbws.util.iso3166 import ISO_3166_ALPHA_2

_ALPHANUM = 'abcdefghijklmnopqrstuvwxyz'
_ALPHANUM += _ALPHANUM.upper()
_ALPHANUM += '0123456789'

_SYMBOLS_NO_QUOTES = '!@#$%^&*()-_=+\\|[]{}:;/?.,<>'

_HEX = '0123456789ABCDEF'

_LOG_LEVELS = ['debug', 'info', 'warning', 'error', 'critical']

log = logging.getLogger(__name__)


def _expand_path(path):
    """Expand path string containing shell variables and ~ constructions
    into their values. Environment variables have to have their $ escaped by
    another $. For example: $$XDG_RUNTIME_DIR/foo.bar
    """
    return os.path.expanduser(os.path.expandvars(path))


def _extend_config(conf, fname):
    """Extend ConfigParser from file configuration."""
    log.debug('Reading config file %s', fname)
    with open(fname, 'rt') as fd:
        conf.read_file(fd, source=fname)
    return conf


def _get_default_config():
    """Return ConfigParser with default configuration."""
    conf = ConfigParser(interpolation=ExtendedInterpolation(),
                        converters={'path': _expand_path})
    return _extend_config(conf, DEFAULT_CONFIG_PATH)


def _obtain_user_conf_path():
    if os.environ.get("SUPERVISED") == "1":
        return SUPERVISED_USER_CONFIG_PATH
    return USER_CONFIG_PATH


def _get_user_config(args, conf=None):
    """Get user configuration.
    Search for user configuration in the default path or the path passed as
    argument and extend the configuration if they are found.
    """
    if not conf:
        conf = ConfigParser(interpolation=ExtendedInterpolation(),
                            converters={'path': _expand_path})
    else:
        assert isinstance(conf, ConfigParser)
    if args.config:
        if not os.path.isfile(args.config):
            # XXX: The logger is not configured at this stage,
            # sbws should start with a logger before reading configurations.
            print('Configuration file %s not found, using defaults.' %
                  args.config)
            return conf
        print('Using configuration provided as argument %s' % args.config)
        return _extend_config(conf, args.config)
    user_config_path = _obtain_user_conf_path()
    if os.path.isfile(user_config_path):
        print('Using configuration file %s' % user_config_path)
        return _extend_config(conf, user_config_path)
    log.debug('No user config found, using defaults.')
    return conf


def _get_default_logging_config(conf=None):
    """Get default logging configuration."""
    if not conf:
        conf = ConfigParser(interpolation=ExtendedInterpolation(),
                            converters={'path': _expand_path})
    else:
        assert isinstance(conf, ConfigParser)
    return _extend_config(conf, DEFAULT_LOG_CONFIG_PATH)


def get_config(args):
    """Get ConfigParser interpolating all configuration files."""
    conf = _get_default_config()
    conf = _get_default_logging_config(conf=conf)
    conf = _get_user_config(args, conf=conf)
    return conf


def _can_log_to_file(conf):
    '''
    Checks all the known reasons for why we might not be able to log to a file,
    and returns whether or not we think we will be able to do so. This is
    useful because if we can't log to a file, we might want to force logging to
    stdout.

    If we can't log to file, return False and the reason. Otherwise return True
    and an empty string.
    '''
    # We won't be able to get paths.log_dname from the config when we are first
    # initializing sbws because it depends on paths.sbws_home (by default).
    # If there is an issue getting this option, tell the caller that we can't
    # log to file.
    try:
        conf.getpath('paths', 'log_dname')
    except InterpolationMissingOptionError as e:
        return False, e
    return True, ''


def configure_logging(args, conf):
    assert isinstance(conf, ConfigParser)
    logger = 'logger_sbws'
    # Set the correct handler(s) based on [logging] options
    handlers = set()
    can_log_to_file, reason = _can_log_to_file(conf)
    if not can_log_to_file or conf.getboolean('logging', 'to_stdout'):
        # always add to_stdout if we cannot log to file
        handlers.add('to_stdout')
    if can_log_to_file and conf.getboolean('logging', 'to_file'):
        handlers.add('to_file')
    if conf.getboolean('logging', 'to_syslog'):
        handlers.add('to_syslog')
    # Collect the handlers in the appropriate config option
    conf[logger]['handlers'] = ','.join(handlers)
    if 'to_file' in handlers:
        # This is weird.
        #
        # Python's logging library expects 'args' to be a tuple ... but it has
        # to be stored as a string and it evals() the string.
        #
        # The first argument is the file name to which it should log. Set it to
        # the sbws command (like 'scanner' or 'generate') if possible, or to
        # 'sbws' failing that.
        dname = conf.getpath('paths', 'log_dname')
        os.makedirs(dname, exist_ok=True)
        fname = os.path.join(dname, '{}.log'.format(args.command or 'sbws'))
        # The second argument is the file mode, and it should be left alone
        mode = 'a'
        # The third is the maximum file size (in bytes) each log file should be
        max_bytes = conf.getint('logging', 'to_file_max_bytes')
        # And the forth is the number of backups to keep
        num_backups = conf.getint('logging', 'to_file_num_backups')
        # Now store those things as a string in the config. So dumb.
        conf['handler_to_file']['args'] = \
            str((fname, mode, max_bytes, num_backups))
    # Set some stuff that needs config parser's interpolation
    conf['formatter_to_file']['format'] = conf['logging']['to_file_format']
    conf['formatter_to_stdout']['format'] = conf['logging']['to_stdout_format']
    conf['formatter_to_syslog']['format'] = conf['logging']['to_syslog_format']
    conf[logger]['level'] = conf['logging']['level'].upper()
    conf['handler_to_file']['level'] = conf['logging']['to_file_level'].upper()
    conf['handler_to_stdout']['level'] = \
        conf['logging']['to_stdout_level'].upper()
    conf['handler_to_syslog']['level'] = \
        conf['logging']['to_syslog_level'].upper()
    # If there's a log_level cli argument, the user would expect that level
    # in the standard output.
    # conf['logging']['level'] sets the lower level, but it's still needed to
    # set the stdout level.
    # It also must be set up in the end, since cli arguments have higher
    # priority.
    if args.log_level:
        conf['logging']['level'] = args.log_level.upper()
        conf['handler_to_stdout']['level'] = conf['logging']['level']
    # Now we configure the standard python logging system
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
    errors.extend(_validate_scanner(conf))
    errors.extend(_validate_tor(conf))
    errors.extend(_validate_paths(conf))
    errors.extend(_validate_destinations(conf))
    errors.extend(_validate_relayprioritizer(conf))
    errors.extend(_validate_logging(conf))
    return len(errors) < 1, errors


def _validate_cleanup(conf):
    errors = []
    sec = 'cleanup'
    err_tmpl = Template('$sec/$key ($val): $e')
    ints = {
        'data_files_compress_after_days': {'minimum': 1, 'maximum': None},
        'data_files_delete_after_days': {'minimum': 1, 'maximum': None},
        'v3bw_files_compress_after_days': {'minimum': 1, 'maximum': None},
        'v3bw_files_delete_after_days': {'minimum': 1, 'maximum': None},
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
        'circuit_timeout': {'minimum': 1, 'maximum': None},
    }
    floats = {
        'http_timeout': {'minimum': 0.0, 'maximum': None},
    }
    bools = {
        'reset_bw_ipv4_changes': {},
        'reset_bw_ipv6_changes': {},
    }
    all_valid_keys = list(ints.keys()) + list(floats.keys()) + \
        list(bools.keys())
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl))
    errors.extend(_validate_section_ints(conf, sec, ints, err_tmpl))
    errors.extend(_validate_section_floats(conf, sec, floats, err_tmpl))
    errors.extend(_validate_section_bools(conf, sec, bools, err_tmpl))
    return errors


def _obtain_sbws_home(conf):
    sbws_home = conf.getpath('paths', 'sbws_home')
    # No need for .sbws when this is the default home
    if sbws_home == "/var/lib/sbws/.sbws":
        conf['paths']['sbws_home'] = os.path.dirname(sbws_home)


def _obtain_run_dpath(conf):
    """Set runtime directory when sbws is run by a system service."""
    xdg = os.environ.get('XDG_RUNTIME_DIR')
    if os.environ.get('SUPERVISED') == "1":
        conf['tor']['run_dpath'] = SUPERVISED_RUN_DPATH
    elif xdg is not None:
        conf['tor']['run_dpath'] = os.path.join(xdg, 'sbws', 'tor')


def _validate_paths(conf):
    _obtain_sbws_home(conf)
    errors = []
    sec = 'paths'
    err_tmpl = Template('$sec/$key ($val): $e')
    unvalidated_keys = [
        'datadir', 'sbws_home', 'v3bw_fname', 'v3bw_dname', 'state_fname',
        'log_dname']
    all_valid_keys = unvalidated_keys
    allow_missing = ['sbws_home']
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl,
                                         allow_missing=allow_missing))
    return errors


def _validate_country(conf, sec, key, err_tmpl):
    errors = []
    if conf[sec].get(key, None) is None:
        errors.append(err_tmpl.substitute(
            sec=sec, key=key, val=None,
            e="Missing country in configuration file."))
        return errors
    valid = conf[sec]['country'] in ISO_3166_ALPHA_2
    if not valid:
        errors.append(err_tmpl.substitute(
            sec=sec, key=key, val=conf[sec][key],
            e="Not a valid ISO 3166 alpha-2 country code."))
    return errors


def _validate_scanner(conf):
    errors = []
    sec = 'scanner'
    err_tmpl = Template('$sec/$key ($val): $e')
    ints = {
        'num_rtts': {'minimum': 0, 'maximum': 100},
        'num_downloads': {'minimum': 1, 'maximum': 100},
        'initial_read_request': {'minimum': 1, 'maximum': None},
        'measurement_threads': {'minimum': 1, 'maximum': None},
        'min_download_size': {'minimum': 1, 'maximum': None},
        'max_download_size': {'minimum': 1, 'maximum': None},
    }
    floats = {
        'download_toofast': {'minimum': 0.001, 'maximum': None},
        'download_min': {'minimum': 0.001, 'maximum': None},
        'download_target': {'minimum': 0.001, 'maximum': None},
        'download_max': {'minimum': 0.001, 'maximum': None},
    }
    all_valid_keys = list(ints.keys()) + list(floats.keys()) + \
        ['nickname', 'country']
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl))
    errors.extend(_validate_section_ints(conf, sec, ints, err_tmpl))
    errors.extend(_validate_section_floats(conf, sec, floats, err_tmpl))
    valid, error_msg = _validate_nickname(conf[sec], 'nickname')
    if not valid:
        errors.append(err_tmpl.substitute(
            sec=sec, key='nickname', val=conf[sec]['nickname'], e=error_msg))
    errors.extend(_validate_country(conf, sec, 'country', err_tmpl))
    return errors


def _validate_tor(conf):
    _obtain_run_dpath(conf)
    errors = []
    sec = 'tor'
    err_tmpl = Template('$sec/$key ($val): $e')
    unvalidated_keys = [
        'datadir', 'run_dpath', 'control_socket', 'pid', 'log', 'extra_lines']
    all_valid_keys = unvalidated_keys
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl))
    return errors


def _validate_relayprioritizer(conf):
    errors = []
    sec = 'relayprioritizer'
    err_tmpl = Template('$sec/$key ($val): $e')
    ints = {
        'min_relays': {'minimum': 1, 'maximum': None},
    }
    floats = {
        'fraction_relays': {'minimum': 0.0, 'maximum': 1.0},
    }
    bools = {
        'measure_authorities': {},
    }
    all_valid_keys = list(ints.keys()) + list(floats.keys()) +\
        list(bools.keys())
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl))
    errors.extend(_validate_section_ints(conf, sec, ints, err_tmpl))
    errors.extend(_validate_section_floats(conf, sec, floats, err_tmpl))
    errors.extend(_validate_section_bools(conf, sec, bools, err_tmpl))
    return errors


def _validate_logging(conf):
    errors = []
    sec = 'logging'
    err_tmpl = Template('$sec/$key ($val): $e')
    enums = {
        'level': {'choices': _LOG_LEVELS},
        'to_file_level': {'choices': _LOG_LEVELS},
        'to_stdout_level': {'choices': _LOG_LEVELS},
        'to_syslog_level': {'choices': _LOG_LEVELS},
    }
    bools = {
        'to_file': {},
        'to_stdout': {},
        'to_syslog': {},
    }
    ints = {
        'to_file_max_bytes': {'minimum': 0, 'maximum': None},
        'to_file_num_backups': {'minimum': 0, 'maximum': None},
    }
    unvalidated = ['format', 'to_file_format', 'to_stdout_format',
                   'to_syslog_format']
    all_valid_keys = list(bools.keys()) + list(enums.keys()) + \
        list(ints.keys()) + unvalidated
    errors.extend(_validate_section_keys(conf, sec, all_valid_keys, err_tmpl))
    errors.extend(_validate_section_bools(conf, sec, bools, err_tmpl))
    errors.extend(_validate_section_enums(conf, sec, enums, err_tmpl))
    return errors


def _validate_destinations(conf):
    errors = []
    sec = 'destinations'
    section = conf[sec]
    err_tmpl = Template('$sec/$key ($val): $e')
    dest_sections = []
    for key in section.keys():
        if key == 'usability_test_interval':
            value = section[key]
            valid, error_msg = _validate_int(section, key, minimum=1)
            if not valid:
                errors.append(err_tmpl.substitute(
                    sec=sec, key=key, val=value, e=error_msg))
            continue
        value = section[key]
        valid, error_msg = _validate_boolean(section, key)
        if not valid:
            errors.append(err_tmpl.substitute(
                sec=sec, key=key, val=value, e=error_msg))
            continue
        assert valid
        if section.getboolean(key):
            dest_sections.append('{}.{}'.format(sec, key))
    urls = {
        'url': {},
    }
    all_valid_keys = list(urls.keys()) + ['verify', 'country']
    for sec in dest_sections:
        if sec not in conf:
            errors.append('{} is an enabled destination but is not a '
                          'section in the config'.format(sec))
            continue
        errors.extend(_validate_section_keys(
            conf, sec, all_valid_keys, err_tmpl, allow_missing=['verify']))
        errors.extend(_validate_section_urls(conf, sec, urls, err_tmpl))
        errors.extend(_validate_country(conf, sec, 'country', err_tmpl))
    return errors


def _validate_section_keys(conf, sec, keys, tmpl, allow_missing=None):
    if allow_missing is None:
        allow_missing = []
    errors = []
    section = conf[sec]
    # Find keys that exist in the user's config that are not known
    for key in section:
        if key not in keys:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key], e='Unknown key'))
    # Find keys that don't exist in the user's config that should
    for key in keys:
        if key not in section and key not in allow_missing:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val='[NOT SET]', e='Missing key'))
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


def _validate_section_urls(conf, sec, urls, tmpl):
    errors = []
    section = conf[sec]
    for key in urls:
        valid, error = _validate_url(section, key)
        if not valid:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key],
                e='Not a valid url ({})'.format(error)))
    return errors


def _validate_section_enums(conf, sec, enums, tmpl):
    errors = []
    section = conf[sec]
    for key in enums:
        choices = enums[key]['choices']
        valid, error = _validate_enum(section, key, choices)
        if not valid:
            errors.append(tmpl.substitute(
                sec=sec, key=key, val=section[key],
                e='Not a valid enum choice ({})'.format(', '.join(choices))))
    return errors


def _validate_enum(section, key, choices):
    value = section[key]
    if value not in choices:
        return False, '{} not in allowed choices: {}'.format(
            value, ', '.join(choices))
    return True, ''


def _validate_url(section, key):
    value = section[key]
    url = urlparse(value)
    if not url.netloc:
        return False, 'Does not appear to contain a hostname'
    # It should be possible to have an URL that starts by http:// that uses
    # TLS,but python requests is just checking the scheme starts by https
    # when verifying certificate:
    # https://github.com/requests/requests/blob/master/requests/adapters.py#L215  # noqa
    # When the scheme is https but the protocol is not TLS, requests will hang.
    if url.scheme != 'https' and not url.netloc.startswith('127.0.0.1'):
        return False, 'URL scheme must be HTTPS (except for the test server)'
    return True, ''


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


def _validate_nickname(section, key):
    alphabet = _ALPHANUM + _SYMBOLS_NO_QUOTES
    min_len = 1
    max_len = 32
    return _validate_string(section, key, min_len=min_len, max_len=max_len,
                            alphabet=alphabet)


def _validate_string(section, key, min_len=None, max_len=None, alphabet=None,
                     starts_with=None):
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
    if starts_with is not None:
        if not s.startswith(starts_with):
            return False, '{} does not start with {}'.format(s, starts_with)
    return True, ''
