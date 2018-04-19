from ..util.simpleauth import authenticate_to_server
from ..util.sockio import (make_socket, close_socket)
from sbws.globals import time_now
from sbws.lib.circuitbuilder import GapsCircuitBuilder as CB
import sbws.util.stem as stem_utils
from stem.descriptor.router_status_entry import RouterStatusEntryV3
from threading import RLock
import random
import logging
import time

log = logging.getLogger(__name__)


class HelperRelay:
    def __init__(self, conf_section):
        self._fp = conf_section['relay']
        self._server_host = conf_section['server_host']
        self._server_port = conf_section.getint('server_port')
        self._password = conf_section['password']
        self._name = conf_section.name.split('.')[1]

    @property
    def name(self):
        return self._name

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
        assert len(helpers) > 0
        for helper in helpers:
            assert isinstance(helper, HelperRelay)
        self._socks_proxy = (conf['tor']['socks_host'],
                             conf.getint('tor', 'socks_port'))
        self._all_helpers = helpers
        self._usable_helpers = set()
        self._circuit_builder = CB(args, conf, controller)
        self._last_reachability_test = 0
        self._reachability_test_every = \
            conf.getint('helpers', 'reachability_test_every')
        self._reachability_lock = RLock()

    @staticmethod
    def from_config(args, conf, controller=None):
        ''' Returns a new HelperRelayList and an empty string if everything
        goes okay loading HelperRelays from the given config file. Otherwise,
        returns None and an error string '''
        assert 'helpers' in conf
        section = conf['helpers']
        helpers = []
        for key in section.keys():
            if key == 'reachability_test_every':
                continue
            if not section.getboolean(key):
                log.debug('%s is disabled; not loading it', key)
                continue
            helper_sec = 'helpers.{}'.format(key)
            assert helper_sec in conf  # validate_config should require this
            log.debug('Loading info for helper %s', key)
            helpers.append(HelperRelay(conf[helper_sec]))
        if len(helpers) < 1:
            return None, 'No enabled helpers in config'
        return HelperRelayList(args, conf, helpers, controller=controller), ''

    def _should_perform_reachability_test(self):
        return self._last_reachability_test + self._reachability_test_every <\
            time_now()

    def _build_circuit_with_relay(self, relay):
        assert isinstance(relay, RouterStatusEntryV3)
        cb = self._circuit_builder
        # Try three times to get a circuit ending at the target relay
        # Note that the CircuitBuilder may try each path multiple times (as of
        # the time of this comment's writing, it does)
        for _ in range(0, 3):
            circ_id = cb.build_circuit([None, relay.fingerprint])
            if circ_id is not None:
                return circ_id
        return None

    def _helper_server_is_functioning(self, helper, circ_id):
        assert circ_id
        cb = self._circuit_builder
        sock = make_socket(*self._socks_proxy)
        connected = stem_utils.connect_over_circuit(
            cb.controller, circ_id, sock, helper.server_host,
            helper.server_port)
        if not connected:
            close_socket(sock)
            return False
        authed = authenticate_to_server(sock, helper.password)
        close_socket(sock)
        return authed

    def _perform_reachability_test(self):
        self._reachability_lock.acquire()
        log.debug('Performing reachability tests')
        helpers = set()
        for helper in self._all_helpers:
            fp = helper.fingerprint
            relay = stem_utils.fp_or_nick_to_relay(self.controller, fp)
            if not relay:
                log.warning('Helper %s\'s relay with fp %s does not seem to '
                            'be in the consensus. Ignoring it.', helper.name,
                            fp[0:8])
                continue
            circ_id = self._build_circuit_with_relay(relay)
            if not circ_id:
                log.warning('Unable to build a circuit with helper %s\'s '
                            'relay %s in it. Ignoring it.', helper.name,
                            relay.nickname)
                continue
            if not self._helper_server_is_functioning(helper, circ_id):
                log.warning('Unable to speak with the sbws server for helper '
                            '%s. Ignoring it.', helper.name)
                self._circuit_builder.close_circuit(circ_id)
                continue
            self._circuit_builder.close_circuit(circ_id)
            log.debug('Helper %s is usable. Keeping it.', relay.nickname)
            helpers.add(helper)
        self._last_reachability_test = time_now()
        self._usable_helpers = list(helpers)
        log.info('After performing reachability tests, we have %d/%d usable '
                 'helpers: %s', len(self._usable_helpers),
                 len(self._all_helpers),
                 ', '.join([h.name for h in self._usable_helpers]))
        self._reachability_lock.release()

    def next(self, blacklist=[]):
        ''' Returns the next helper in the list that should be used. Do not
        pick a helper that has a relay with a fingerprint in the given
        blacklist. Returns None if no valid helper is available. '''
        with self._reachability_lock:
            while True:
                if self._should_perform_reachability_test():
                    self._perform_reachability_test()
                if len(self._usable_helpers) > 0:
                    break
                time_till_next_check = self._reachability_test_every + 0.001
                log.warning('Of our %d configured helpers, none are usable at '
                            'this time. Sleeping %f seconds on this blocking '
                            'call to HelperRelayList.next() until we can '
                            'check for a usable helper again.',
                            len(self._all_helpers), time_till_next_check)
                time.sleep(time_till_next_check)
        assert not self._should_perform_reachability_test()
        random.shuffle(self._usable_helpers)
        for helper in self._usable_helpers:
            if helper.fingerprint in blacklist:
                continue
            return helper
        return None
