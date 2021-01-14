.. _torflow_aggr:

Torflow measurements aggregation
==================================

Torflow aggregation or scaling goal is:

From Torflow's `README.spec.txt`_ (section 2.2)::

    In this way, the resulting network status consensus bandwidth values
    are effectively re-weighted proportional to how much faster the node
    was as compared to the rest of the network.

With and without PID control
----------------------------

Per relay measurements' bandwidth
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

They are calculated in the same way whether or not `PID controller`_ feedback
is used.

From Torflow's `README.spec.txt`_ (section 1.6)::

    The strm_bw field is the average (mean) of all the streams for the relay
    identified by the fingerprint field.

    The filt_bw field is computed similarly, but only the streams equal to
    or greater than the strm_bw are counted in order to filter very slow
    streams due to slow node pairings.

In the code, `SQLSupport.py`_, ``strm_bw`` is ``sbw`` and
``filt_bw`` is ``filt_sbws``::

    for rs in RouterStats.query.filter(stats_clause).\
          options(eagerload_all('router.streams.circuit.routers')).all():
      tot_sbw = 0
      sbw_cnt = 0
      for s in rs.router.streams:
        if isinstance(s, ClosedStream):
          skip = False
          #for br in badrouters:
          #  if br != rs:
          #    if br.router in s.circuit.routers:
          #      skip = True
          if not skip:
            # Throw out outliers < mean
            # (too much variance for stddev to filter much)
            if rs.strm_closed == 1 or s.bandwidth() >= rs.sbw:
              tot_sbw += s.bandwidth()
              sbw_cnt += 1

    if sbw_cnt: rs.filt_sbw = tot_sbw/sbw_cnt
    else: rs.filt_sbw = None

This is also expressed in pseudocode in the `bandwidth file spec`_, section B.4
step 1.

Calling ``bw_i`` to ``strm_bw`` and ``bwfilt_i`` to ``filt_bw``,
if ``bw_j`` is a measurement for a relay ``i`` and ``m`` is the number of
measurements for that relay, then:

.. math::

    bw_i = \mu(bw_j) = \frac{\sum_{j=1}^{m}bw_j}{m}

.. math::

    bwfilt_i &= \mu(max(\mu(bw_j), bw_j))
              = \frac{\sum_{j=1}^{m} max\left(\frac{\sum_{j=1}^{m}bw_j}{m}, bw_j\right)}{m}

Network measurements' bandwidth average
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

From `README.spec.txt`_ (section 2.1)::

    Once we have determined the most recent measurements for each node, we
    compute an average of the filt_bw fields over all nodes we have measured.

In Torflow's `aggregate.py`_ code::

    filt_avg = sum(map(lambda n: n.filt_bw, nodes.itervalues()))/float(len(nodes))
    strm_avg = sum(map(lambda n: n.strm_bw, nodes.itervalues()))/float(len(nodes))

Both in the code with PID and without, all types of nodes get the same
average.

This is also expressed in pseudocode in the `bandwidth file spec`_, section B.4
step 2.

Calling ``bwstrm`` to ``strm_avg`` and ``bwfilt`` to ``fitl_avg``, if ``n`` is
the number of relays in the network, then:

.. math::

   bwstrm &= \mu(bw_i)
           = \frac{\sum_{i=1}^{n}bw_i}{n}
           = \frac{\sum_{i=1}^{n} \frac{\sum_{j=1}^{m}bw_j}{m} }{n}

.. math::

   bwfilt &= \mu(bwfilt_i)
           = \frac{\sum_{i=1}^{n}bwfilt_i}{n}
           = \frac{\sum_{i=1}^{n}\frac{\sum_{j=1}^{m}max(\mu(bw_j), bw_j)}{m}}{n}
           = \frac{\sum_{i=1}^{n}\frac{\sum_{j=1}^{m}max\left(\frac{\sum_{j=1}^{m}bw_j}{m}, bw_j\right)}{m}}{n}


Per relay bandwidth ratio
~~~~~~~~~~~~~~~~~~~~~~~~~

From `README.spec.txt`_ (section 2.2)::

    These averages are used to produce ratios for each node by dividing the
    measured value for that node by the network average.

In Torflow's `aggregate.py`_ code::

    for n in nodes.itervalues():
        n.fbw_ratio = n.filt_bw/true_filt_avg[n.node_class()]
        n.sbw_ratio = n.strm_bw/true_strm_avg[n.node_class()]

    [snip]

    # Choose the larger between sbw and fbw
      if n.sbw_ratio > n.fbw_ratio:
        n.ratio = n.sbw_ratio
      else:
        n.ratio = n.fbw_ratio

This is also expressed in pseudocode in the `bandwidth file spec`_, section B.4
step 2 and 3.

Calling ``rf_i`` to ``fbw_ratio`` and ``rs_i`` to ``sbw_ration`` and ``r_i``
to ``ratio``:

.. math::

    rf_i = \frac{bwfilt_i}{bwfilt}

    rs_i = \frac{bw_i}{bwstrm}


.. math::

    r_i = max(rf_i, rs_i)
        = max\left(\frac{bwfilt_i}{bwfilt}, \frac{bw_i}{bwstrm}\right)
        = max\left(\frac{bwfilt_i}{\mu(bwfilt_i)}, \frac{bw_i}{\mu(bwfilt_i)}\right)

Per relay descriptors bandwidth
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

From `TorCtl.py`_ code, it is the minimum of all the descriptor bandwidth
values::

    bws = map(int, g)
    bw_observed = min(bws)

    [snip]

    return Router(ns.idhex, ns.nickname, bw_observed, dead, exitpolicy,
    ns.flags, ip, version, os, uptime, published, contact, rate_limited,
    ns.orhash, ns.bandwidth, extra_info_digest, ns.unmeasured)

Because of the matched regular expression, ``bws`` is **not** all the descriptor
bandwidth values, but the observed bandwidth and the burst bandwidth, ie., it
does not take the average bandwidth, what seems to be a bug in Torflow.

This is passed to ``Router``, in which the consensus bandwidth is assigned to the
descriptor bandwidth when there is no consensus bandwidth::

    (idhex, name, bw, down, exitpolicy, flags, ip, version, os, uptime,
       published, contact, rate_limited, orhash,
       ns_bandwidth,extra_info_digest,unmeasured) = args

    [snip]

    if ns_bandwidth != None:
      self.bw = max(ns_bandwidth,1) # Avoid div by 0
    else:
      self.bw = max(bw,1) # Avoid div by 0

    [snip]

    self.desc_bw = max(bw,1) # Avoid div by 0

And written by `SQLSupport.py`_ as descriptor and conensus bandwidth::

      f.write(" desc_bw="+str(int(cvt(s.avg_desc_bw,0))))
      f.write(" ns_bw="+str(int(cvt(s.avg_bw,0)))+"\n")

Without PID control
-------------------

Per relay scaled bandwidth
~~~~~~~~~~~~~~~~~~~~~~~~~~

From `README.spec.txt`_ (section 2.2)::

    These ratios are then multiplied by the most recent observed descriptor
    bandwidth we have available for each node, to produce a new value for
    the network status consensus process.

In `aggregate.py`_ code::

    n.new_bw = n.desc_bw*n.ratio

This is also expressed in pseudocode in the `bandwidth file spec`_, section B.4
step 5.

Calling ``bwnew_i`` to ``new_bw`` and ``descbw_i`` to ``use_bw``:

.. math::

    descbw_i = min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right)

    bwnew_i =& descbw_i \times r_i \

            &= min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right) \times max(rf_i, rs_i) \

            &= min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right) \times max\left(\frac{bwfilt_i}{bwfilt}, \frac{bw_i}{bwstrm}\right) \

            &= min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right) \times max\left(\frac{bwfilt_i}{\mu(bwfilt_i)}, \frac{bw_i}{\mu(bw_i)}\right)


With PID control
----------------

Per relay descriptors bandwidth
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Even though `README.spec.txt`_ talks about the consensus bandwidth, in
`aggregate.py`_ code, the consensus bandwidth is never used, since
``use_desc_bw`` is initialized to True and never changed::

    self.use_desc_bw = True

    [snip]

    if cs_junk.bwauth_pid_control:
      if cs_junk.use_desc_bw:
        n.use_bw = n.desc_bw
      else:
        n.use_bw = n.ns_bw

Per relay scaled bandwidth
~~~~~~~~~~~~~~~~~~~~~~~~~~

From `README.spec.txt`_ section 3.1::

   The bandwidth authorities measure F_node: the filtered stream
   capacity through a given node (filtering is described in Section 1.6).

   [snip]

   pid_error = e(t) = (F_node - F_avg)/F_avg.

   [snip]

   new_consensus_bw = old_consensus_bw +
                        old_consensus_bw * K_p * e(t) +
                        old_consensus_bw * K_i * \integral{e(t)} +
                        old_consensus_bw * K_d * \derivative{e(t)}

   [snip]

   For the case where K_p = 1, K_i=0, and K_d=0, it can be seen that this
   system is equivalent to the one defined in 2.2, except using consensus
   bandwidth instead of descriptor bandwidth:

       new_bw = old_bw + old_bw*e(t)
       new_bw = old_bw + old_bw*(F_node/F_avg - 1)
       new_bw = old_bw*F_node/F_avg
       new_bw = old_bw*ratio

In Torflow's code, this is actually the case and most of the code is not
executed because the default ``K`` values.

It seems then that ``F_node`` is ``filt_bw`` in Torflow's code or ``bwfilt_i``
here, and ``F_avg`` is ``filt_avg`` in Torflow's code or ``bwfilt`` here.

In `aggregate.py`_ code, pid error also depends on which of the ratios is
greater::

    if cs_junk.use_best_ratio and n.sbw_ratio > n.fbw_ratio:
            n.pid_error = (n.strm_bw - true_strm_avg[n.node_class()]) \
                            / true_strm_avg[n.node_class()]
            else:
            n.pid_error = (n.filt_bw - true_filt_avg[n.node_class()]) \
                            / true_filt_avg[n.node_class()]

    [snip]

    n.new_bw = n.use_bw + cs_junk.K_p*n.use_bw*n.pid_error

Calling ``e_i`` to ``pid_error``, in the case that ``rs_i`` > ``rf_i``:

.. math::

    e_i = \frac{bw_i - bwstrm}{bwstrm} = \frac{bw_i}{bwstrm} - 1

    bwn_i = descbw_i + descbw_i \times e_i = descbw_i \times (1 + e_i)
          = descbw_i \times (1 + \frac{bw_i}{bwstrm} - 1)
          = descbw_i \times \frac{bw_i}{bwstrm} = descbw_i \times rs_i

And in the case that ``rs_i`` < ``rf_i``:

.. math::

    e_i = \frac{bwfilt_i - bwfilt}{bwfilt} = \frac{bwfilt_i}{bwfilt} - 1

    bwn_i = descbw_i + descbw_i \times e_i = descbw_i \times (1 + e_i)
          = descbw_i \times (1 + \frac{bwfilt_i}{bwfilt} - 1)
          = descbw_i \times \frac{bwfilt_i}{bwfilt} = descbw_i \times rf_i

So, it is the same as the scaled bandwidth in the case without PID controller,
ie.:

.. math::

    bwn_i = descbw_i \times max(rf_i, rs_i)

With and without PID control
----------------------------

Per relay scaled bandwidth limit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once each relay bandwidth is scaled, it is limited to a maximum, that is
calculated as the sum of all the relays in the current consensus scaled
bandwidth per 0.05.

From `aggregate.py`_ code::

    NODE_CAP = 0.05

    [snip]

    if n.idhex in prev_consensus:
      if prev_consensus[n.idhex].bandwidth != None:
        prev_consensus[n.idhex].measured = True
        tot_net_bw += n.new_bw

    [snip]

    if n.new_bw > tot_net_bw*NODE_CAP:
      [snip]
      n.new_bw = int(tot_net_bw*NODE_CAP)


.. math::

   bwn_i =& min\left(bwnew_i,
              \sum_{i=1}^{n}bwnew_i \times 0.05\right) \

         &= min\left(
              \left(min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right) \times r_i\right),
                \sum_{i=1}^{n}\left(min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right) \times r_i\right)
                \times 0.05\right)\

         &= min\left(
              \left(min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right) \times max\left(rf_i, rs_i\right)\right),
                \sum_{i=1}^{n}\left(min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right) \times
                  max\left(rf_i, rs_i\right)\right) \times 0.05\right)\

         &= min\left(
              \left(min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right) \times max\left(\frac{bwfilt_i}{bwfilt},
                  \frac{bw_i}{bwstrm}\right)\right),
                \sum_{i=1}^{n}\left(min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right) \times
                  max\left(\frac{bwfilt_i}{bwfilt},
                    \frac{bw_i}{bwstrm}\right)\right) \times 0.05\right)

.. math::

      bwn_i = min\left(
              \left(min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right) \times max\left(\frac{bwfilt_i}{bwfilt},
                  \frac{bw_i}{bwstrm}\right)\right),
                \sum_{i=1}^{n}\left(min\left(bwobs_i, bwavg_i, bwburst_i, measuredconsensusbw_i \right) \times
                  max\left(\frac{bwfilt_i}{bwfilt},
                    \frac{bw_i}{bwstrm}\right)\right) \times 0.05\right)


Per relay scaled bandwidth rounding
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, the new scaled bandwidth is expressed in kilobytes and rounded a number
of digits.

Differences between Torflow aggregation and sbws scaling (May 2020)
-------------------------------------------------------------------

Torflow does not exclude relays because of having "few" measurements or "close"
to each other for that relay.

If there are not new measurements for a relay, Torflow uses the previous
calculated bandwidth, instead of the new value::

      # If there is a new sample, let's use it for all but guards
      if n.measured_at > prev_votes.vote_map[n.idhex].measured_at:

      [snip]

      else:
          # Reset values. Don't vote/sample this measurement round.
          n.revert_to_vote(prev_votes.vote_map[n.idhex])

The oldest measurements Toflow seems to take are from 4 weeks ago, while sbws
oldest measurements are 5 days old::

    GUARD_SAMPLE_RATE = 2*7*24*60*60 # 2wks

    [snip]

    MAX_AGE = 2*GUARD_SAMPLE_RATE

    [snip]

                # old measurements are probably
                # better than no measurements. We may not
                # measure hibernating routers for days.
                # This filter is just to remove REALLY old files
                if time.time() - timestamp > MAX_AGE:


.. _README.spec.txt: https://gitweb.torproject.org/torflow.git/tree/NetworkScanners/BwAuthority/README.spec.txt
.. _PID Controller: https://en.wikipedia.org/wiki/PID_controller
.. _SQLSupport.py: https://gitweb.torproject.org/pytorctl.git/tree/SQLSupport.py#n493
.. _bandwidth file spec: https://gitweb.torproject.org/torspec.git/tree/bandwidth-file-spec.txt
.. _aggregate.py: https://gitweb.torproject.org/torflow.git/tree/NetworkScanners/BwAuthority/aggregate.py
.. _TorCtl.py: https://gitweb.torproject.org/pytorctl.git/tree/TorCtl.py
