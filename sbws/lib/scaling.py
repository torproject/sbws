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
    mu = mean(bw_measurements)
    bws_gte_mean = filter(lambda bw: bw >= mu, bw_measurements)
    return mean(bws_gte_mean)
