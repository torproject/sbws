.. _differences:

Differences between Torflow and sbws
====================================

(Last updated 2020-02-18)

Aggregating measurements and scaling
------------------------------------

Filtering
~~~~~~~~~

Torflow does not exclude relays because of having "few" measurements or "close"
to each other for that relay, like sbws does :ref:`filtering-measurements`.

However this is currently disabled in sbws.

Network stream and filtered bandwidth
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Torflow calculates the network stream and filtered averages by type of relay
:ref:`stream-and-filtered-bandwidth-for-all-relays`, while sbws is not taking
into account the type of relay :ref:`scaling-the-bandwidth-measurements`.

Values from the previous Bandwidth File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

sbws is not reading the previous Bandwidth File, but scaling all the values
with the raw measurements.

Instead, Torflow uses the previous Bandwidth File values in some cases:

- When a relay measurement is older than the one in the previous
  Bandwidth File, it uses all the values from the previous Bandwidth File.
  (how is possible that the Bandwidth File would have a newer measurements?)::

    self.new_bw = prev_vote.bw * 1000

Bandwidth File KeyValues
~~~~~~~~~~~~~~~~~~~~~~~~

sbws does not calculate nor write to the Bandwidth file the ``pid`` variables
and KeyValues that are used in Torflow. Example of Torflow KeyValues not in sbws::

  measured_at=1613547098 updated_at=1613547098 pid_error=11.275680184 pid_error_sum=11.275680184 pid_bw=23255048 pid_delta=11.0140582849 circ_fail=0.0

sbws does not have ``measured_at`` and ``updated_at`` either.

Currently the scaled bandwidth in Torflow does not depend on those extra values
and they seem to be just informative.
