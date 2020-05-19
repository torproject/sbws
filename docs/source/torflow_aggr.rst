.. _torflow_aggr:

Torflow measurements aggregation
==================================

From Torflow's README.spec.txt (section 2.2)::

    In this way, the resulting network status consensus bandwidth values  # NOQA
    are effectively re-weighted proportional to how much faster the node  # NOQA
    was as compared to the rest of the network.

The variables and steps used in Torflow:

**strm_bw**::

    The strm_bw field is the average (mean) of all the streams for the relay  # NOQA
    identified by the fingerprint field.
    strm_bw = sum(bw stream x)/|n stream|

**filt_bw**::

    The filt_bw field is computed similarly, but only the streams equal to  # NOQA
    or greater than the strm_bw are counted in order to filter very slow  # NOQA
    streams due to slow node pairings.

**filt_sbw and strm_sbw**::

    for rs in RouterStats.query.filter(stats_clause).\
          options(eagerload_all('router.streams.circuit.routers')).all():  # NOQA
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

**filt_avg, and strm_avg**::

    Once we have determined the most recent measurements for each node, we  # NOQA
    compute an average of the filt_bw fields over all nodes we have measured.  # NOQA

::

    filt_avg = sum(map(lambda n: n.filt_bw, nodes.itervalues()))/float(len(nodes))  # NOQA
    strm_avg = sum(map(lambda n: n.strm_bw, nodes.itervalues()))/float(len(nodes))  # NOQA

**true_filt_avg and true_strm_avg**::

    for cl in ["Guard+Exit", "Guard", "Exit", "Middle"]:
        true_filt_avg[cl] = filt_avg
        true_strm_avg[cl] = strm_avg

In the non-pid case, all types of nodes get the same avg

**n.fbw_ratio and n.fsw_ratio**::

    for n in nodes.itervalues():
        n.fbw_ratio = n.filt_bw/true_filt_avg[n.node_class()]
        n.sbw_ratio = n.strm_bw/true_strm_avg[n.node_class()]

**n.ratio**::

    These averages are used to produce ratios for each node by dividing the  # NOQA
    measured value for that node by the network average.

::

    # Choose the larger between sbw and fbw
      if n.sbw_ratio > n.fbw_ratio:
        n.ratio = n.sbw_ratio
      else:
        n.ratio = n.fbw_ratio

**desc_bw**:

It is the minimum of all the descriptor bandwidth values::

    bws = map(int, g)
    bw_observed = min(bws)

    return Router(ns.idhex, ns.nickname, bw_observed, dead, exitpolicy,
    ns.flags, ip, version, os, uptime, published, contact, rate_limited,  # NOQA
    ns.orhash, ns.bandwidth, extra_info_digest, ns.unmeasured)

    self.desc_bw = max(bw,1) # Avoid div by 0

**new_bw**::

    These ratios are then multiplied by the most recent observed descriptor  # NOQA
    bandwidth we have available for each node, to produce a new value for  # NOQA
    the network status consensus process.

::

    n.new_bw = n.desc_bw*n.ratio

The descriptor observed bandwidth is multiplied by the ratio.

**Limit the bandwidth to a maximum**::

    NODE_CAP = 0.05

::

    if n.new_bw > tot_net_bw*NODE_CAP:
      plog("INFO", "Clipping extremely fast "+n.node_class()+" node "+n.idhex+"="+n.nick+  # NOQA
            " at "+str(100*NODE_CAP)+"% of network capacity ("+
            str(n.new_bw)+"->"+str(int(tot_net_bw*NODE_CAP))+") "+
            " pid_error="+str(n.pid_error)+
            " pid_error_sum="+str(n.pid_error_sum))
      n.new_bw = int(tot_net_bw*NODE_CAP)

However, tot_net_bw does not seems to be updated when not using pid.
This clipping would make faster relays to all have the same value.

All of that can be expressed as:

.. math::

    bwn_i =& min\\left(bwnew_i,
              \\sum_{i=1}^{n}bwnew_i \\times 0.05\\right) \\

          &= min\\left(
              \\left(min\\left(bwobs_i, bwavg_i, bwbur_i \\right) \\times r_i\\right),
                \\sum_{i=1}^{n}\\left(min\\left(bwobs_i, bwavg_i, bwbur_i \\right) \\times r_i\\right)
                \\times 0.05\\right)\\

          &= min\\left(
              \\left(min\\left(bwobs_i, bwavg_i, bwbur_i \\right) \\times max\\left(rf_i, rs_i\\right)\\right),
                \\sum_{i=1}^{n}\\left(min\\left(bwobs_i, bwavg_i, bwbur_i \\right) \\times
                  max\\left(rf_i, rs_i\\right)\\right) \\times 0.05\\right)\\

          &= min\\left(
              \\left(min\\left(bwobs_i, bwavg_i, bwbur_i \\right) \\times max\\left(\\frac{bwfilt_i}{bwfilt},
                  \\frac{bw_i}{bwstrm}\\right)\\right),
                \\sum_{i=1}^{n}\\left(min\\left(bwobs_i, bwavg_i, bwbur_i \\right) \\times
                  max\\left(\\frac{bwfilt_i}{bwfilt},
                    \\frac{bw_i}{bwstrm}\\right)\\right) \\times 0.05\\right)
