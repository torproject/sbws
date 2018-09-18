.. _config_tor:

sbws scanner tor configuration
-------------------------------

At the time of writing, sbws sets the following torrc options for the following
reasons when it launches Tor. You can find them in ``sbws/globals.py`` and
``sbws/util/stem.py``.

- ``SocksPort auto``: To proxy requests over Tor.
- ``CookieAuthentication 1``: The easiest way to authenticate to Tor.
- ``LearnCircuitBuildTimeout 0``: To keep circuit build timeouts static.
- ``CircuitBuildTimeout 10``: To give up on struggling circuits sooner.
- ``UseEntryGuards 0``: To avoid path bias warnings.
- ``DataDirectory ...``: To set Tor's datadirectory to be inside sbws's.
- ``PidFile ...``: To make it easier to tell if Tor is running.
- ``ControlSocket ...``: To control Tor.
- ``Log notice ...``: To know what the heck is going on.
