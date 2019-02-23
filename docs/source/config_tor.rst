.. _config_tor:

Internal Tor configuration for the scanner
------------------------------------------

The scanner needs an specific Tor configuration.
The following options are either set when launching Tor or required when
connection to an existing Tor daemon.

Default configuration:

- ``SocksPort auto``: To proxy requests over Tor.
- ``CookieAuthentication 1``: The easiest way to authenticate to Tor.
- ``UseEntryGuards 0``: To avoid path bias warnings.
- ``UseMicrodescriptors 0``: Because full server descriptors are needed.
- ``SafeLogging 0``: Useful for logging, since there's no need for anonymity.
- ``LogTimeGranularity 1``
- ``ProtocolWarnings 1``
- ``LearnCircuitBuildTimeout 0``: To keep circuit build timeouts static.

Configuration that depends on the user configuration file:

- ``CircuitBuildTimeout ...``: The timeout trying to build a circuit.
- ``DataDirectory ...``: The Tor data directory path.
- ``PidFile ...``: The Tor PID file path.
- ``ControlSocket ...``: The Tor control socket path.
- ``Log notice ...``: The Tor log level and path.

Configuration that needs to be set on runtime:

- ``__DisablePredictedCircuits 1``: To build custom circuits.
- ``__LeaveStreamsUnattached 1``

Currently most of the code that sets this configuration is in :func:`sbws.util.stem.launch_tor`
and the default configuration is ``sbws/globals.py``.

.. note:: the location of these code is being refactored.