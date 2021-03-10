from statistics import mean


def bw_measurements_from_results(results):
    return [
        dl['amount'] / dl['duration']
        for r in results for dl in r.downloads
    ]


def bw_filt(bw_measurements):
    """Filtered bandwidth for a relay.

    It is the equivalent to Torflow's ``filt_sbw``.
    ``mu`` in this function is the equivalent to Torflow's ``sbw``.
    """
    # It's safe to return 0 here, because:
    # 1. this value will be the numerator when calculating the ratio.
    # 2. `kb_round_x_sig_dig` returns a minimum of 1.
    # This should never be the case, as the measurements come from successful
    # results.
    if not bw_measurements:
        return 0
    # Torflow is rounding to an integer, so is `bw_mean_from_results` in
    # `v3bwfile.py`
    mu = round(mean(bw_measurements))
    bws_gte_mean = list(filter(lambda bw: bw >= mu, bw_measurements))
    if bws_gte_mean:
        return round(mean(bws_gte_mean))
    return 1


def network_means_by_relay_type(bw_lines, router_statuses_d):
    # Temporarily assign the type of relay to calculate network stream and
    # filtered bandwidth by type
    for line in bw_lines:
        rs = None
        if router_statuses_d:
            rs = router_statuses_d.get(line.node_id.replace("$", ""), None)
        line.set_relay_type(rs_relay_type(rs))

    mu_type = muf_type = {}
    for rt in RELAY_TYPES:
        bw_lines_type = [line for line in bw_lines if line.relay_type == rt]
        if len(bw_lines_type) > 0:
            # Torflow does not round these values.
            # Ensure they won't be 0 to avoid division by 0 Exception
            mu_type[rt] = mean([line.bw_mean for line in bw_lines_type]) or 1
            muf_type[rt] = mean([line.bw_filt for line in bw_lines_type]) or 1
    return mu_type, muf_type
