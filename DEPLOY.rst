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

Install sbws according to ``./INSTALL.rst`` (or `/INSTALL.rst </INSTALL.rst>`_
or :ref:`install`).

To run the ``scanner`` it is mandatory to create a configuration file with at
least one ``destination``.

If ``sbws`` is installed from the Debian package, then create a file in
``/etc/sbws/sbws.ini`` like in the following example:

.. literalinclude:: /examples/sbws.example.ini
    :caption: Example sbws.example.ini

If ``sbws`` is installed from the sources as a non-root user then create the
file in ``~/.sbws.ini``.

More details about the configuration file can be found in
``./docs/source/man_sbws.ini.rst`` (or `/docs/source/man_sbws.ini.rst <man_sbws.ini>`_
or :doc:`man_sbws.ini` or ``man sbws.ini``)

See also ``./docs/source/man_sbws.rst`` (or `/docs/source/man_sbws.rst <man_sbws>`_ or
:doc:`man_sbws` or ``man sbws``) manual page.
