.. _config_tor:

Internal Tor configuration for the scanner
------------------------------------------

The scanner needs a specific Tor configuration.
The following options are either set when launching Tor or required when
connection to an existing Tor daemon.

Default configuration:

- ``CookieAuthentication 1``: The easiest way to authenticate to Tor.
- ``UseEntryGuards 0``: To avoid path bias warnings.
- ``UseMicrodescriptors 0``: Because full server descriptors are needed.
- ``SafeLogging 0``: Useful for logging, since there's no need for anonymity.
- ``LogTimeGranularity 1``
- ``ProtocolWarnings 1``
- ``FetchDirInfoEarly 1``
- ``FetchDirInfoExtraEarly 1``: Respond to `MaxAdvertisedBandwidth` as soon as possible.
- ``FetchUselessDescriptors 1``: Keep fetching descriptors, even when idle.
- ``LearnCircuitBuildTimeout 0``: To keep circuit build timeouts static.

Configuration that depends on the user configuration file:

- ``CircuitBuildTimeout ...``: The timeout trying to build a circuit.
- ``DataDirectory ...``: The Tor data directory path.
- ``PidFile ...``: The Tor PID file path.
- ``ControlSocket ...``: The Tor control socket path.
- ``Log notice ...``: The Tor log level and path.

Configuration that needs to be set on runtime:

- ``__DisablePredictedCircuits 1``: To build custom circuits.
- ``__LeaveStreamsUnattached 1``: The scanner is attaching the streams itself.

Configuration that can be set on runtime and fail:

- ``ConnectionPadding 0``: Useful for avoiding extra traffic, since scanner anonymity is not a goal.

Currently most of the code that sets this configuration is in :func:`sbws.util.stem.launch_tor`
and the default configuration is ``sbws/globals.py``.

.. note:: the location of this code is being refactored.
