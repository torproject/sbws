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

It is not required, but it is recomended to include a custom scanner
``nickname`` in ``config.ini``.

Destination(s) configuration in more detail::

    [destinations]
    foo = on
    bar = on
    baz = off

    [destinations.foo]
    url = http://example.org/sbws.bin

    [destinations.bar]
    url = https://example.com/data

    [destinations.baz]
    url = https://example.net/ask/stan/where/the/file/is.exe

``foo`` demonstrates a typical case.

``bar`` demonstrates a case where you want to use HTTPS and want to assume the
large file for sbws to download is at its default path (probably
``/sbws.bin``).

``baz`` demonstrates a disabled destination that sbws will ignore.

