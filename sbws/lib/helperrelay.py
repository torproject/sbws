import random
import sbws.util.stem as stem_utils
import logging

log = logging.getLogger(__name__)


class HelperRelay:
    def __init__(self, conf_section):
        self._fp = conf_section['relay']
        self._server_host = conf_section['server_host']
        self._server_port = conf_section.getint('server_port')
        self._password = conf_section['password']

    @property
    def fingerprint(self):
        return self._fp

    @property
    def server_host(self):
        return self._server_host

    @property
    def server_port(self):
        return self._server_port

    @property
    def password(self):
        return self._password


class HelperRelayList:
    def __init__(self, args, conf, helpers, controller=None):
        if controller is None:
            c, error_msg = stem_utils.init_controller_with_config(conf)
            assert c, error_msg
            self.controller = c
        else:
            self.controller = controller
        for helper in helpers:
            assert isinstance(helper, HelperRelay)
        self.helpers = helpers

    @staticmethod
    def from_config(args, conf, controller=None):
        ''' Returns a new HelperRelayList and an empty string if everything
        goes okay loading HelperRelays from the given config file. Otherwise,
        returns None and an error string '''
        assert 'helpers' in conf
        section = conf['helpers']
        helpers = []
        for key in section.keys():
            if not section.getboolean(key):
                log.debug('%s is disabled; not loading it', key)
                continue
            helper_sec = 'helpers.{}'.format(key)
            assert helper_sec in conf  # validate_config should require this
            log.debug('Loading info for helper %s', key)
            helpers.append(HelperRelay(conf[helper_sec]))
        return HelperRelayList(
            args, conf, helpers, controller=controller), ''

    def next(self, blacklist=[]):
        ''' Returns the next helper in the list that should be used. Do not
        pick a helper that has a relay with a fingerprint in the given
        blacklist. Returns None if no valid helper is available. '''
        # XXX: Consider alternate designs. This just picks a random
        # non-blacklisted helper. What if we could keep track of the health of
        # the helpers? What if we picked geographically close helpers (probably
        # in a different function called pick_best() or something)? What if we
        # picked a helper that hasn't been used recently for this relay?
        #
        # Ideally we should see if the helper is online. It should be easy to
        # do since the list has a copy of the stem controller. Just see if
        # there's a descriptor for the given fingerprint.
        random.shuffle(self.helpers)
        for helper in self.helpers:
            if helper.fingerprint in blacklist:
                continue
            return helper
        return None
