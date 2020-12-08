from stem import CircuitExtensionFailed, InvalidRequest, ProtocolError, Timeout
from stem import InvalidArguments, ControllerError, SocketClosed
import logging

log = logging.getLogger(__name__)


def valid_circuit_length(path):
    return 0 < len(path) <= 8


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
    # XXX: In new major version, remove args and conf, they are not used.
    def __init__(self, args, conf, controller, relay_list=None,
                 close_circuits_on_exit=True):
        self.controller = controller
        self.built_circuits = set()
        self.close_circuits_on_exit = close_circuits_on_exit
        self.circuit_timeout = conf.getint('general', 'circuit_timeout')

    def close_circuit(self, circ_id):
        try:
            self.controller.close_circuit(circ_id)
        # SocketClosed will be raised when stopping sbws
        except (InvalidArguments, InvalidRequest, SocketClosed) as e:
            log.debug(e)
        self.built_circuits.discard(circ_id)

    def _build_circuit_impl(self, path):
        """
        :returns tuple: circuit id if the circuit was built, error if there
            was an error building the circuit.
        """
        if not valid_circuit_length(path):
            return None, "Can not build a circuit, invalid path."
        c = self.controller
        timeout = self.circuit_timeout
        fp_path = '[' + ' -> '.join([p for p in path]) + ']'
        log.debug('Building %s', fp_path)
        try:
            circ_id = c.new_circuit(
                path, await_build=True, timeout=timeout)
        except (InvalidRequest, CircuitExtensionFailed,
                ProtocolError, Timeout, SocketClosed) as e:
            return None, str(e)
        return circ_id, None

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


# In a future refactor, remove this class, since sbws chooses the relays to
# build the circuit, the relays are not just choosen as random as this class
# does.
class GapsCircuitBuilder(CircuitBuilder):
    """Same as ``CircuitBuilder`` but implements build_circuit."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    def build_circuit(self, path):
        """Return parent class build circuit method.

        Since sbws is only building 2 hop paths, there is no need to add random
        relays to the path, or convert back and forth between fingerprint and
        ``Relay`` objects.

        """
        return self._build_circuit_impl(path)
