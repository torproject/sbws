.. _deploy:

Deploying Simple Bandwidth Scanner
=====================================

To run sbws is needed:

- A machine to run the :term:`scanner`.
- One or more :term:`destination` (s) that serve a large file.

Both the ``scanner`` and your the ``destination``(s) should be on fast,
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

To configure destinations, create a configuration file according to
``./docs/source/man_sbws.ini.rst`` (or `/docs/source/man_sbws.ini.rst <man_sbws.ini>`_
or :doc:`man_sbws.ini` or ``man sbws.ini``)

See also ``/docs/source/man_sbws.rst`` (or `/docs/source/man_sbws.rst`_ or
:doc:`man_sbws` or ``man sbws``) manual page.
