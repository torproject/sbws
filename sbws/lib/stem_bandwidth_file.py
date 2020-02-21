"""Stem's Bandwidth file HEADER_ATTR part as it is in stem's commit
658dd5281604eb9c63a91e529501947ecc65ef6b, which will be included in the next
Stem's release, 1.8.0, except ``_date`` because depends on other stem's module.
"""
# XXX: Remove this file when stem releases 1.8.0.
from ..util.timestamp import isostr_to_dt_obj

# Converts header attributes to a given type. Malformed fields should be
# ignored according to the spec.

def _str(val):
  return val  # already a str


def _int(val):
  return int(val) if (val and val.isdigit()) else None


def _date(val):
  try:
    return isostr_to_dt_obj(val)
  except ValueError:
    return None  # not an iso formatted date


def _csv(val):
  return map(lambda v: v.strip(), val.split(',')) if val is not None else None


# mapping of attributes => (header, type)

HEADER_ATTR = {
  # version 1.1.0 introduced headers

  'version': ('version', _str),

  'software': ('software', _str),
  'software_version': ('software_version', _str),

  'earliest_bandwidth': ('earliest_bandwidth', _date),
  'latest_bandwidth': ('latest_bandwidth', _date),
  'created_at': ('file_created', _date),
  'generated_at': ('generator_started', _date),

  # version 1.2.0 additions

  'consensus_size': ('number_consensus_relays', _int),
  'eligible_count': ('number_eligible_relays', _int),
  'eligible_percent': ('percent_eligible_relays', _int),
  'min_count': ('minimum_number_eligible_relays', _int),
  'min_percent': ('minimum_percent_eligible_relays', _int),

  # version 1.3.0 additions

  'scanner_country': ('scanner_country', _str),
  'destinations_countries': ('destinations_countries', _csv),

  # version 1.4.0 additions

  'time_to_report_half_network': ('time_to_report_half_network', _int),

  'recent_stats.consensus_count': ('recent_consensus_count', _int),
  'recent_stats.prioritized_relay_lists': ('recent_priority_list_count', _int),
  'recent_stats.prioritized_relays': ('recent_priority_relay_count', _int),
  'recent_stats.measurement_attempts': ('recent_measurement_attempt_count', _int),
  'recent_stats.measurement_failures': ('recent_measurement_failure_count', _int),
  'recent_stats.relay_failures.no_measurement': ('recent_measurements_excluded_error_count', _int),
  'recent_stats.relay_failures.insuffient_period': ('recent_measurements_excluded_near_count', _int),
  'recent_stats.relay_failures.insufficient_measurements': ('recent_measurements_excluded_few_count', _int),
  'recent_stats.relay_failures.stale': ('recent_measurements_excluded_old_count', _int),
}
