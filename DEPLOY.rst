.. _deploy:

Deploying Simple Bandwidth Scanner
=====================================

To run sbws is needed:

- A machine to run the :term:`scanner`.
- One or more :term:`destination` (s) that serve a large file.

Both the ``scanner`` and your the ``destination`` (s) should be on fast,
well connected machines.

.. _destinations_requirements:

destination requirements
------------------------------------

- A Web server installed and running that supports HTTP GET, HEAD and
  Range (:rfc:`7233`) requests.
  ``Apache`` HTTP Server and ``Nginx`` support them.
- Optional support for TLS
- A large file; at the time of writing, at least 1 GiB in size

scanner setup
----------------------

Install sbws according to `<INSTALL.rst>`_ (in the local directory or GitHub)
or `<INSTALL.html>`_  (local build or Read the Docs).

To configure destinations, create a configuration file according to
``./docs/source/man_sbws.ini.rst`` (in the local directory or GitHub) or
`<man_sbws.ini.html>`_  (local build or Read the Docs) or
``man sbws.ini`` (Debian).

See also ``./docs/source/man_sbws.rst`` (in the local directory or GitHub) or
`<man_sbws.html>`_ (local build or Read the Docs) or ``man sbws`` (Debian).
