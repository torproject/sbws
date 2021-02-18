.. _differences:

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
