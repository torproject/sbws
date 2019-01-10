import logging
import random

from stem import (CircuitExtensionFailed, ControllerError, InvalidArguments,
                  InvalidRequest, ProtocolError, Timeout)

from .relaylist import Relay

log = logging.getLogger(__name__)


class PathLengthException(Exception):
    def __init__(self, message=None, errors=None):
        if message is not None:
            super().__init__(message)
        else:
            super().__init__()
        self.errors = errors


def valid_circuit_length(path):
    assert isinstance(path, int) or isinstance(path, list)
    if isinstance(path, int):
        return path > 0 and path <= 8
    return len(path) > 0 and len(path) <= 8


class CircuitBuilder:
    ''' The CircuitBuilder interface.

    Subclasses must implement their own build_circuit() function.
    Subclasses may keep additional state if they'd find it helpful.

    The primary way to use a CircuitBuilder of any type is to simply create it
    and then call cb.build_circuit(...) with any options that your
    CircuitBuilder type needs.

    It might be good practice to close circuits as you find you no longer need
    them, but CircuitBuilder will keep track of existing circuits and close
    them when it is deleted.
    '''
    def __init__(self, args, conf, controller, relay_list,
                 close_circuits_on_exit=True):
        self.controller = controller
        self.rng = random.SystemRandom()
        self.relay_list = relay_list
        self.built_circuits = set()
        self.close_circuits_on_exit = close_circuits_on_exit
        self.circuit_timeout = conf.getint('general', 'circuit_timeout')

    @property
    def relays(self):
        return self.relay_list.relays

    def build_circuit(self, *a, **kw):
        ''' Implementations of this method should build the circuit and return
        its (str) ID. If it cannot be built, it should return None. '''
        raise NotImplementedError()

    def close_circuit(self, circ_id):
        c = self.controller
        try:
            c.get_circuit(circ_id, default=None)
            try:
                c.close_circuit(circ_id)
            except (InvalidArguments, InvalidRequest):
                pass
            self.built_circuits.discard(circ_id)
        except (ControllerError, ValueError) as e:
            log.exception("Error trying to get circuit to close it: %s.", e)

    def _build_circuit_impl(self, path):
        """
        :returns tuple: circuit id if the circuit was built, error if there
            was an error building the circuit.
        """
        if not valid_circuit_length(path):
            raise PathLengthException()
        c = self.controller
        timeout = self.circuit_timeout
        fp_path = '[' + ' -> '.join([p for p in path]) + ']'
        log.debug('Building %s', fp_path)
        error = None
        for _ in range(0, 3):
            try:
                circ_id = c.new_circuit(
                    path, await_build=True, timeout=timeout)
            except (InvalidRequest, CircuitExtensionFailed,
                    ProtocolError, Timeout) as e:
                log.debug(e)
                error = str(e)
                continue
            else:
                return circ_id, None
        return None, error

    def __del__(self):
        c = self.controller
        if not self.close_circuits_on_exit:
            return
        for circ_id in self.built_circuits:
            try:
                c.get_circuit(circ_id, default=None)
                try:
                    c.close_circuit(circ_id)
                except (InvalidArguments, InvalidRequest):
                    pass
            except (ControllerError, InvalidArguments) as e:
                log.exception("Exception trying to get circuit to delete: %s",
                              e)
        self.built_circuits.clear()


class GapsCircuitBuilder(CircuitBuilder):
    ''' The build_circuit member function takes a list. Falsey values in the
    list will be replaced with relays chosen uniformally at random; Truthy
    values will be assumed to be relays. '''
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    def _normalize_path(self, path):
        ''' Change fingerprints/nicks to relay descriptor and change Falsey
        values to None. Return the new path, or None if error '''
        new_path = []
        for fp in path:
            if not fp:
                new_path.append(None)
                continue
            relay = Relay(fp, self.controller)
            if not relay.fingerprint:
                log.debug('Tor seems to no longer think %s is a relay', fp)
                return None
            new_path.append(relay)
        return new_path

    def _random_sample_relays(self, number, blacklist):
        ''' Get <number> random relays from self.relays that are not in the
        blacklist. Return None if it cannot be done because too many are
        blacklisted. Otherwise return a list of relays. '''
        all_fps = [r.fingerprint for r in self.relays]
        black_fps = [r.fingerprint for r in blacklist]
        if len(black_fps) + number > len(all_fps):
            return None
        chosen_fps = []
        while len(chosen_fps) < number:
            choice = self.rng.choice(all_fps)
            if choice in black_fps:
                continue
            chosen_fps.append(choice)
            black_fps.append(choice)
        return [Relay(fp, self.controller) for fp in chosen_fps]

    def build_circuit(self, path):
        ''' <path> is a list of relays and Falsey values. Relays can be
        specified by fingerprint or nickname, and fingerprint is highly
        recommended. Falsey values (like None) will be replaced with relays
        chosen uniformally at random. A relay will not be in a circuit twice.
        '''
        if not valid_circuit_length(path):
            raise PathLengthException()
        path = self._normalize_path(path)
        if path is None:
            return None
        num_missing = len(['foo' for r in path if not r])
        insert_relays = self._random_sample_relays(
            num_missing, [r for r in path if r is not None])
        if insert_relays is None:
            path = ','.join([r.nickname if r else str(None) for r in path])
            log.warning(
                'Problem building a circuit to satisfy %s with available '
                'relays in the network', path)
            return None
        assert len(insert_relays) == num_missing
        path = [r.fingerprint if r else insert_relays.pop().fingerprint
                for r in path]
        return self._build_circuit_impl(path)
