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

- A Web server installed and running that supports HEAD and GET
  requests (``apache`` and ``nginx`` fit this description)
- Optional support for TLS
- A large file; at the time of writing, at least 1 GiB in size

:term:`scanner` setup
----------------------

Install sbws according to :doc:`/INSTALL`.

``sbws`` needs :term:`destination` (s) to request files from.
They are not included by default.

Inside |dotsbws| you will find ``config.ini``. Open it with a text editor. it
should be very simple. Let's give our scanner a nickname. Add the following
lines

::

    [scanner]
    nickname = D0ntD3@dOpen!nside

(Pick your own nickname. This one just demonstrates that you can use almost any
character)

Congratulations, you've learned how to add a section to your config file and
how to add an option to a section.

Remeber |dests|? We need to add them to ``config.ini``. We're going to assume
you have two you are ready to use and one that isn't quite ready yet.

::

    [destinations]
    foo = on
    bar = on
    baz = off

    [destinations.foo]
    url = http://fooshoomoo.com/sbws.bin

    [destinations.bar]
    url = https://barstoolsinc.com

    [destinations.baz]
    url = https://bazistan.com/ask/stan/where/the/file/is.exe

``foo`` demonstrates a typical case.

``bar`` demonstrates a case where you want to use HTTPS and want to assume the
large file for sbws to download is at its default path (probably
``/sbws.bin``).

``baz`` demonstrates a disabled destination that sbws will ignore.

