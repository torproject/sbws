Frequently Asked Questions (FAQ)
==================================

.. note:: even thought this questions should be answered by reading the
   :doc:`specification`, here the answers should be short and clear.

.. note:: You may also enjoy the :doc:`glossary`.

How many hops are the circuits used to perform the measurements?
------------------------------------------------------------------

.. todo:: see :ref:`XX`

Two hops: the relay to be measured and the :term:`helper relay`.

How are relays selected to be measured?
---------------------------------------

The :term:`sbws scanner` periodically refreshes its idea for what relays should
be measured next. It prioritizese the measurement of relays that do not have
recent results. In this way, relays that have just joined the network or have
just come back online after a many-day period of being offline will be measured
before relays that have been online constantly.

Is it the sbws scanner or server that gives the v3bw file to the directory authority?
-------------------------------------------------------------------------------------

Technically, neither.

In the suggested setup, the machine running :term:`sbws scanner` continuously
will also periodically run :term:`sbws generate` to produce a :term:`v3bw file`
for the :term:`bandwidth authority` to read.

.. todo:: see :ref:`XX`


Is it the sbws scanner or server that I need to run close to a fast relay?
-------------------------------------------------------------------------

The :term:`sbws server`.

Why doesn't sbws just use a web/file server instead of custom software?
-----------------------------------------------------------------------

To lower protocol overhead and to allow :term:`sbws scanners <sbws scanner>` to
request a wide range of bytes.

Sbws essentially has no overhead, with only about 70 bytes used in a handshake
at the beginning of each connection. A connection can be used to perform
multiple measurements of one relay.

At the time of writing, sbws scanners are allowed to request from the
:term:`server <sbws server>` between 1 byte and 1,073,741,824 bytes (1 GiB).
That's a lot of possibilities and a ton of storage space.

.. todo::

    Look more into the viability of using an HTTP(S) server using HTTP basic
    authentication and range requests to control how many bytes to download.
    Determine if many requests (and therefore measurements) can be made over a
    single stream. Determine how much overhead HTTP adds and make a judgement
    call on whether it is worth it.

Why is there authentication between sbws scanner and sbws server?
-----------------------------------------------------------------

So random people on the Internet cannot discover an :term:`sbws server` and ask
it to repeatedly send large amounts of data or otherwise abuse it.

What ports does sbws use by default?
------------------------------------

- **31648/tcp**: The :term:`sbws server` listens on this port by default. It
  does not need to be reachable from the Internet, but only from the
  :term:`helper relay` near it.
