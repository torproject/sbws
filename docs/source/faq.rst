Frequently Asked Questions (FAQ)
==================================

.. note:: even thought this questions should be answered by reading the
   :doc:`specification`, here the answers should be short and clear.

What is a bandwidth authority?
-----------------------------------

.. todo:: see :ref:`XX`

A server that runs ``sbws scanner``, the bandwidth scanner that performs the
measurements. It can run on the same machine as a directory authority or
somehow send its results to it.

How many hops are the circuits used to perform the measurements?
------------------------------------------------------------------

.. todo:: see :ref:`XX`

Two hops: the relay to be measured and the helper relay.

How are relays selected to be measured?
---------------------------------------

.. todo:: see :ref:`prioritization`

What is a helper relay?
-----------------------

.. todo:: see :ref:`XX`

Is it the sbws scanner or server that gives the v3bw files to the directory authority?
-------------------------------------------------------------------------------------

Technically, neither.

In the suggested setup, the machine running ``sbws scanner`` continuously will
also periodically run ``sbws generate`` to produce a v3bw file for the
directory authority to read.

.. todo:: see :ref:`XX`


Is it the sbws scanner or server that I need to run close to a fast relay?
-------------------------------------------------------------------------

The sbws server.

.. todo:: see :ref:`XX`

Why doesn't sbws just use a web/file server instead of custom software?
-----------------------------------------------------------------------

To lower protocol overhead and to allow sbws scanners to request a wide range of
bytes.

Sbws essentially has no overhead, with only about 70 bytes used in a handshake
at the beginning of each connection. A connection can be used to perform
multiple measurements of one relay.

At the time of writing, sbws scanners are allowed to request from the server
between 1 byte and 1,073,741,824 bytes (1 GiB). That's a lot of possibilities
and a ton of storage space.

.. todo:: see :ref:`XX`

Why is there authentication between sbws clien and sbws server?
---------------------------------------------------------------

So random people on the Internet cannot discover an sbws server and ask it to
repeatedly send large amounts of data or otherwise abuse it.

.. todo:: see :ref:`XX`
