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
    mu = 1
    if bw_measurements:
        mu = mean(bw_measurements)
    bws_gte_mean = list(filter(lambda bw: bw >= mu, bw_measurements))
    if bws_gte_mean:
        return mean(bws_gte_mean)
    return 1
