from stem import (CircuitExtensionFailed, InvalidRequest)
from stem import Flag
import random
import util.stem as stem_utils


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
    def __init__(self, close_circuits_on_exit=True):
        self.controller = stem_utils.init_controller()
        self.relays = self._init_relays()
        self.built_circuits = set()
        self.close_circuits_on_exit = close_circuits_on_exit

    def _init_relays(self):
        c = self.controller
        assert stem_utils.is_controller_okay(c)
        return [ns for ns in c.get_network_statuses()]

    def build_circuit(self, *a, **kw):
        ''' Implementations of this method should build the circuit and return
        its (str) ID. If it cannot be built, it should return None. '''
        raise NotImplementedError()

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
        for _ in range(0, 3):
            try:
                circ_id = c.new_circuit(path, await_build=True)
            except (InvalidRequest, CircuitExtensionFailed) as e:
                print(e)
                continue
            self.built_circuits.add(circ_id)
            return circ_id
        return None

    def fp_or_nick_to_relay(self, fp_nick):
        ''' Takes a string that could be either a relay's fingerprint or
        nickname. Return the relay's descriptor if found.  Otherwise return
        None '''
        assert isinstance(fp_nick, str)
        c = self.controller
        assert stem_utils.is_controller_okay(c)
        return c.get_network_status(fp_nick, default=None)

    def __del__(self):
        c = self.controller
        if not stem_utils.is_controller_okay(c):
            return
        if not self.close_circuits_on_exit:
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
        super().__init__()

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
        self.guards = [self.fp_or_nick_to_relay(g) for g in guards]
        if len(self.guards) > len([g for g in self.guards if g]):
            self.guards = [g for g in self.guards if g]
            print('Warning: couldn\'t find descriptors for all guards. Only '
                  'using:', ', '.join([g.nickname for g in self.guards]))
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
        self.exits = self._init_exits()

    def _init_exits(self):
        relays = self.relays
        return [r for r in relays if Flag.EXIT in r.flags]

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
            relay = self.fp_or_nick_to_relay(fp)
            if not relay:
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
        return [self.fp_or_nick_to_relay(fp) for fp in chosen_fps]

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
            print('Problem building a circuit to satisfy',
                  [r.nickname if r else None for r in path], 'with available '
                  'relays in the network')
            return None
        assert len(insert_relays) == num_missing
        path = [r.fingerprint if r else insert_relays.pop().fingerprint
                for r in path]
        #print('building', '->'.join([r[0:8] for r in path]))
        return self._build_circuit_impl(path)


# pylama:ignore=E265
