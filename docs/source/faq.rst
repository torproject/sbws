Frequently Asked Questions (FAQ)
==================================

.. seealso:: :doc:`glossary`.

How many hops are the circuits used to perform the measurements?
----------------------------------------------------------------

Two hops.

How are relays selected to be measured?
---------------------------------------

The :term:`sbws scanner` periodically refreshes its idea for what relays should
be measured next. It prioritizese the measurement of relays that do not have
recent results. In this way, relays that have just joined the network or have
just come back online after a many-day period of being offline will be measured
before relays that have been online constantly.

How do sbws scanner results end up in the consensus?
----------------------------------------------------

The :term:`sbws scanner` runs continuously to gather fresh data.

The :term:`sbws generate` command takes the fresh data and generates a
:term:`v3bw file`.

The Tor :term:`directory authority` parses the v3bw file and includes bandwidth
information in its vote.

The authorities take the low-median of the bandwidths for each relay from all
of the :term:`bandwidth authorities <bandwidth authority>` and use that in the
consensus.

Does sbws need any open ports?
------------------------------

No.

How much bandwidth will the sbws scanner use?
---------------------------------------------

.. todo:: answer this

How much bandwidth will the webserver use?
------------------------------------------

.. todo:: answer this

Should I run my own webserver? Use a CDN? Something else?
---------------------------------------------------------

It's up to you. Sbws is very flexible.

.. todo:: better answer.
