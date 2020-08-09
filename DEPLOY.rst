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
- TLS support to avoid HTTP content caches at the various exit nodes.
- Certificates can be self-signed.
- A large file; at the time of writing, at least 1 GiB in size
  It can be created running::

      head -c $((1024*1024*1024)) /dev/urandom > 1GiB

- A fixed IP address or a domain name.
- Bandwidth: at least 12.5MB/s (100 Mbit/s).
- Network traffic: around 12-15GB/day.

If possible, use a `Content delivery network`_ (CDN) in order to make the
destination IP closer to the scanner exit.

scanner setup
----------------------

Install sbws according to `<INSTALL.rst>`_ (in the local directory or Tor
Project Gitlab) or `<INSTALL.html>`_  (local build or Read the Docs).

To run the ``scanner`` it is mandatory to create a configuration file with at
least one ``destination``.
It is recommended to set several ``destinations`` so that the ``scanner`` can
continue if one fails.

If ``sbws`` is installed from the Debian package, then create the configuration
file in ``/etc/sbws/sbws.ini``.
You can see an example with all the possible options here, note that you don't
need to include all of that and that everything that starts with ``#`` and
``;`` is a comment:

.. literalinclude:: /examples/sbws.example.ini
    :caption: Example sbws.example.ini

If ``sbws`` is installed from the sources as a non-root user then create the
configuration file in ``~/.sbws.ini``.

More details about the configuration file can be found in
``./docs/source/man_sbws.ini.rst`` (in the local directory or Tor Project
Gitlab) or `<man_sbws.ini.html>`_  (local build or Read the Docs) or
``man sbws.ini`` (system package).

See also ``./docs/source/man_sbws.rst`` (in the local directory or Tor Project
Gitlab) or `<man_sbws.html>`_ (local build or Read the Docs) or ``man sbws``
(system package).

.. _Content delivery network: https://en.wikipedia.org/wiki/Content_delivery_network
