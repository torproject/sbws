from stem.control import Controller
from stem import (SocketError, CircuitExtensionFailed, InvalidRequest)
from stem import Flag
import random


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
        self.controller = CircuitBuilder._init_controller()
        self.relays = self._init_relays()
        self.built_circuits = set()
        self.close_circuits_on_exit = close_circuits_on_exit

    @staticmethod
    def _init_controller_helper(port=None, socket=None):
        assert port is None or socket is None
        assert port is None or isinstance(port, int)
        assert socket is None or isinstance(socket, str)
        try:
            if port:
                c = Controller.from_port(port=port)
            else:
                c = Controller.from_socket_file(path=socket)
        except SocketError:
            return None
        else:
            # TODO: Allow for auth via more than just CookieAuthentication
            c.authenticate()
            return c

    @staticmethod
    def _init_controller():
        c = CircuitBuilder._init_controller_helper(port=9051)
        if c:
            print('Connected to Tor on port 9051')
            return c
        c = CircuitBuilder._init_controller_helper(
            socket='/var/run/tor/control')
        if c:
            print('Connected to Tor on socket /var/run/tor/control')
            return c
        c = CircuitBuilder._init_controller_helper(port=9151)
        if c:
            print('Connected to Tor on port 9151')
            return c
        return None

    def _init_relays(self):
        assert self._is_controller_okay()
        c = self.controller
        return [ns for ns in c.get_network_statuses()]

    def _is_controller_okay(self):
        assert self.controller
        c = self.controller
        return c.is_alive() and c.is_authenticated()

    def build_circuit(self, *a, **kw):
        ''' Implementations of this method should build the circuit and return
        its (str) ID. '''
        raise NotImplementedError()

    def close_circuit(self, circ_id):
        # TODO: might want to just check instead of assert.
        assert self._is_controller_okay()
        c = self.controller
        if c.get_circuit(circ_id, default=None):
            c.close_circuit(circ_id)
            self.built_circuits.discard(circ_id)

    def _build_circuit_impl(self, path):
        if not valid_circuit_length(path):
            raise PathLengthException()
        assert self._is_controller_okay()
        c = self.controller
        try:
            circ_id = c.new_circuit(path, await_build=True)
        except (InvalidRequest, CircuitExtensionFailed) as e:
            print(e)
            return None
        self.built_circuits.add(circ_id)
        return circ_id

    def __del__(self):
        if not self._is_controller_okay():
            return
        if not self.close_circuits_on_exit:
            return
        c = self.controller
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
        self.guards = guards

    def build_circuit(self, length=3):
        ''' builds circuit of <length> and returns its (str) ID. The length
        includes the guard in the first hop position '''
        if not valid_circuit_length(length):
            raise PathLengthException()
        fps = [random.choice(self.guards)] + \
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

    def build_circuit(self, path):
        ''' <path> is a list of relays and Falsey values. Relays can be
        specified by fingerprint or nickname, and fingerprint is highly
        recommended. Falsey values (like None) will be replaced with relays
        chosen uniformally at random '''
        # TODO: There's a small chance that relays chosen randomly will match
        # relays already in the path.
        if not valid_circuit_length(path):
            raise PathLengthException()
        num_missing = len(['foo' for r in path if not r])
        insert_relays = random.sample(self.relays, num_missing)
        path = [r if r else insert_relays.pop().fingerprint for r in path]
        return self._build_circuit_impl(path)


# pylama:ignore=E265
