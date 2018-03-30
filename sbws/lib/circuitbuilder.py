from stem import (CircuitExtensionFailed, InvalidRequest)
import random
import sbws.util.stem as stem_utils
from .relaylist import RelayList


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
    Subclasses probably shouldn't implement their own get_circuit_path().
    Subclasses may keep additional state if they'd find it helpful.

    The primary way to use a CircuitBuilder of any type is to simply create it
    and then call cb.build_circuit(...) with any options that your
    CircuitBuilder type needs.

    It might be good practice to close circuits as you find you no longer need
    them, but CircuitBuilder will keep track of existing circuits and close
    them when it is deleted.
    '''
    def __init__(self, args, conf, log, controller=None,
                 close_circuits_on_exit=True):
        if controller is None:
            c, error_msg = stem_utils.init_controller_with_config(conf)
            assert c, error_msg
            self.controller = c
        else:
            self.controller = controller
        self.log = log
        self.relay_list = RelayList(args, conf, log,
                                    controller=self.controller)
        self.built_circuits = set()
        self.close_circuits_on_exit = close_circuits_on_exit

    @property
    def relays(self):
        return self.relay_list.relays

    def build_circuit(self, *a, **kw):
        ''' Implementations of this method should build the circuit and return
        its (str) ID. If it cannot be built, it should return None. '''
        raise NotImplementedError()

    def get_circuit_path(self, circ_id):
        c = self.controller
        assert stem_utils.is_controller_okay(c)
        circ = c.get_circuit(circ_id, default=None)
        if circ is None:
            return None
        return [relay[0] for relay in circ.path]

    def close_circuit(self, circ_id):
        # TODO: might want to just check instead of assert.
        c = self.controller
        assert stem_utils.is_controller_okay(c)
        if c.get_circuit(circ_id, default=None):
            c.close_circuit(circ_id)
            self.built_circuits.discard(circ_id)

    def _build_circuit_impl(self, path):
        if not valid_circuit_length(path):
            raise PathLengthException()
        c = self.controller
        assert stem_utils.is_controller_okay(c)
        self.log.debug('Building', [p[0:8] for p in path])
        for _ in range(0, 3):
            try:
                circ_id = c.new_circuit(path, await_build=True)
            except (InvalidRequest, CircuitExtensionFailed) as e:
                self.log.info(e)
                continue
            self.built_circuits.add(circ_id)
            return circ_id
        return None

    def __del__(self):
        c = self.controller
        if not self.close_circuits_on_exit:
            return
        if not stem_utils.is_controller_okay(c):
            return
        for circ_id in self.built_circuits:
            if c.get_circuit(circ_id, default=None):
                c.close_circuit(circ_id)
        self.built_circuits.clear()


class RandomCircuitBuilder(CircuitBuilder):
    ''' Builds circuits with each relay having equal probability of being
    selected for any position. There's no promise that the last hop will be
    an exit. '''
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    def build_circuit(self, length=3):
        ''' builds circuit of <length> and returns its (str) ID '''
        if not valid_circuit_length(length):
            raise PathLengthException()
        fps = [r.fingerprint for r in random.sample(self.relays, length)]
        return self._build_circuit_impl(fps)


class GuardedCircuitBuilder(CircuitBuilder):
    ''' Like RandomCircuitBuilder, but the first hop will always be one of
    the specified relays chosen uniformally at random. There's no promise that
    the last hop will be an exit. '''
    def __init__(self, guards, *a, **kw):
        ''' <guards> is a list of relays. A relay can be specified either by
        fingerprint or nickname. Fingerprint is highly recommended. '''
        super().__init__(*a, **kw)
        self.guards = [stem_utils.fp_or_nick_to_relay(self.controller, g)
                       for g in guards]
        if len(self.guards) > len([g for g in self.guards if g]):
            self.guards = [g for g in self.guards if g]
            self.log.warn('Warning: couldn\'t find descriptors for all '
                          'guards. Only using:',
                          ', '.join([g.nickname for g in self.guards]))
            assert len(self.guards) > 0

    def build_circuit(self, length=3):
        ''' builds circuit of <length> and returns its (str) ID. The length
        includes the guard in the first hop position '''
        if not valid_circuit_length(length):
            raise PathLengthException()
        fps = [random.choice(self.guards).fingerprint] + \
            [r.fingerprint for r in random.sample(self.relays, length-1)]
        return self._build_circuit_impl(fps)


class ExitCircuitBuilder(CircuitBuilder):
    ''' Like RandomCircuitBuilder, but the last hop will always be an exit
    chosen uniformally at random. There's no promise that it supports exiting
    to a specific IP/port. '''
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    @property
    def exits(self):
        return self.relay_list.exits

    def build_circuit(self, length=3):
        ''' builds circuit of <length> and returns its (str) ID. '''
        if not valid_circuit_length(length):
            raise PathLengthException()
        fps = [r.fingerprint for r in random.sample(self.relays, length-1)] + \
            [random.choice(self.exits).fingerprint]
        return self._build_circuit_impl(fps)


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
            relay = stem_utils.fp_or_nick_to_relay(self.controller, fp)
            if not relay:
                self.log.debug('Failed to get descriptor for relay', fp)
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
            choice = random.choice(all_fps)
            if choice in black_fps:
                continue
            chosen_fps.append(choice)
            black_fps.append(choice)
        return [stem_utils.fp_or_nick_to_relay(self.controller, fp)
                for fp in chosen_fps]

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
            self.log.warn(
                'Problem building a circuit to satisfy',
                [r.nickname if r else None for r in path], 'with available '
                'relays in the network')
            return None
        assert len(insert_relays) == num_missing
        path = [r.fingerprint if r else insert_relays.pop().fingerprint
                for r in path]
        #self.log.info('building', '->'.join([r[0:8] for r in path]))
        return self._build_circuit_impl(path)


# pylama:ignore=E265
