.. _deploy:

Deploying Simple Bandwidth Scanner
=====================================

So you want to run sbws for yourself. You will need

- A machine to run the :term:`scanner`.
- One or more :term:`destination` (s) that serve a large file.

Both :term:`scanner` and your :term:`destination` (s) should be on fast,
well connected machines.

.. _destinations_requirements:

:term:`destination` requirements
------------------------------------

- A Web server installed and running that supports HTTP GET, HEAD and
  Range (:rfc:`7233`) requests.
  ``Apache`` HTTP Server and ``Nginx`` support them.
- Optional support for TLS
- A large file; at the time of writing, at least 1 GiB in size

:term:`scanner` setup
----------------------

Install sbws according to :doc:`/INSTALL`.

``sbws scanner`` needs :term:`destination` (s) to request files from.
They are not included by default.

To configure destinations, create a configuration file according to
:doc:`man_sbws.ini`
