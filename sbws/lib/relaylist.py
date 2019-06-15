import copy
from datetime import datetime, timedelta

from stem.descriptor.router_status_entry import RouterStatusEntryV3
from stem.descriptor.server_descriptor import ServerDescriptor
from stem import Flag, DescriptorUnavailable, ControllerError
import random
import logging
from threading import Lock

from ..globals import MEASUREMENTS_PERIOD

log = logging.getLogger(__name__)


def remove_old_consensus_timestamps(
        consensus_timestamps, measurements_period=MEASUREMENTS_PERIOD):
    """
    Remove the consensus timestamps that are older than period for which
    the measurements are keep from a list of consensus_timestamps.

    :param list consensus_timestamps:
    :param int measurements_period:
    :returns list: a new list of ``consensus_timestamps``
    """
    oldest_date = datetime.utcnow() - timedelta(measurements_period)
    new_consensus_timestamps = \
        [t for t in consensus_timestamps if t >= oldest_date]
    return new_consensus_timestamps


def valid_after_from_network_statuses(network_statuses):
    """Obtain the consensus Valid-After datetime from the ``document``
    attribute of a ``stem.descriptor.RouterStatusEntryV3``.

    :param list network_statuses:
    returns datetime:
    """
    for ns in network_statuses:
        document = getattr(ns, 'document', None)
        if document:
            valid_after = getattr(document, 'valid_after', None)
            if valid_after:
                return valid_after
    return datetime.utcnow().replace(microsecond=0)


class Relay:
    def __init__(self, fp, cont, ns=None, desc=None, timestamp=None):
        '''
        Given a relay fingerprint, fetch all the information about a relay that
        sbws currently needs and store it in this class. Acts as an abstraction
        to hide the confusion that is Tor consensus/descriptor stuff.

        :param str fp: fingerprint of the relay.
        :param cont: active and valid stem Tor controller connection

        :param datatime timestamp: the timestamp of a consensus
            (RouterStatusEntryV3) from which this relay has been obtained.
        '''
        assert isinstance(fp, str)
        assert len(fp) == 40
        if ns is not None:
            assert isinstance(ns, RouterStatusEntryV3)
            self._ns = ns
        else:
            try:
                self._ns = cont.get_network_status(fp, default=None)
            except (DescriptorUnavailable, ControllerError) as e:
                log.exception("Exception trying to get ns %s", e)
                self._ns = None
        if desc is not None:
            assert isinstance(desc, ServerDescriptor)
            self._desc = desc
        else:
            try:
                self._desc = cont.get_server_descriptor(fp, default=None)
            except (DescriptorUnavailable, ControllerError) as e:
                log.exception("Exception trying to get desc %s", e)
        self._consensus_timestamps = []
        self._add_consensus_timestamp(timestamp)
        # The number of times that a relay is "prioritized" to be measured.
        # It is incremented in ``RelayPrioritizer.best_priority``
        self.relay_recent_priority_list_count = 0
        # The number of times that a relay has been queued to be measured.
        # It is incremented in ``scanner.main_loop``
        self.relay_recent_measurement_attempt_count = 0

    def _from_desc(self, attr):
        if not self._desc:
            return None
        return getattr(self._desc, attr, None)

    def _from_ns(self, attr):
        if not self._ns:
            return None
        return getattr(self._ns, attr, None)

    @property
    def nickname(self):
        return self._from_ns('nickname')

    @property
    def fingerprint(self):
        return self._from_ns('fingerprint')

    @property
    def flags(self):
        return self._from_ns('flags')

    @property
    def exit_policy(self):
        return self._from_desc('exit_policy')

    @property
    def average_bandwidth(self):
        return self._from_desc('average_bandwidth')

    @property
    def burst_bandwidth(self):
        return self._from_desc('burst_bandwidth')

    @property
    def observed_bandwidth(self):
        return self._from_desc('observed_bandwidth')

    @property
    def consensus_bandwidth(self):
        """Return the consensus bandwidth in Bytes.

        Consensus bandwidth is the only bandwidth value that is in kilobytes.
        """
        if self._from_ns('bandwidth') is not None:
            return self._from_ns('bandwidth') * 1000

    @property
    def consensus_bandwidth_is_unmeasured(self):
        # measured appears only votes, unmeasured appears in consensus
        # therefore is_unmeasured is needed to know whether the bandwidth
        # value in consensus is comming from bwauth measurements or not.
        return self._from_ns('is_unmeasured')

    @property
    def address(self):
        return self._from_ns('address')

    @property
    def master_key_ed25519(self):
        """Obtain ed25519 master key of the relay in server descriptors.

        :returns: str, the ed25519 master key base 64 encoded without
                  trailing '='s.

        """
        # Even if this key is called master-key-ed25519 in dir-spec.txt,
        # it seems that stem parses it as ed25519_master_key
        key = self._from_desc('ed25519_master_key')
        if key is None:
            return None
        return key.rstrip('=')

    @property
    def consensus_valid_after(self):
        """Obtain the consensus Valid-After from the document of this relay
        network status.
        """
        network_status_document = self._from_ns('document')
        if network_status_document:
            return getattr(network_status_document, 'valid_after', None)
        return None

    @property
    def last_consensus_timestamp(self):
        if len(self._consensus_timestamps) >= 1:
            return self._consensus_timestamps[-1]
        return None

    def _append_consensus_timestamp_if_later(self, timestamp):
        """Append timestamp to the list of consensus timestamps, if it is later
           than the most recent existing timestamp, or there are no timestamps.
           Should only be called by _add_consensus_timestamp().
           timestamp must not be None, and it must not be zero.
        """
        if not timestamp:
            log.info('Bad timestamp %s, skipping consensus timestamp '
                     'update for  relay %s', timestamp, self.fingerprint)
            return
        # The consensus timestamp list was initialized.
        if self.last_consensus_timestamp is not None:
            # timestamp is more recent than the most recent stored
            # consensus timestamp.
            if timestamp > self.last_consensus_timestamp:
                # Add timestamp
                self._consensus_timestamps.append(timestamp)
        # The consensus timestamp list was not initialized.
        else:
            # Add timestamp
            self._consensus_timestamps.append(timestamp)

    def _add_consensus_timestamp(self, timestamp=None):
        """Add the consensus timestamp in which this relay is present.
        """
        # It is possible to access to the relay's consensensus Valid-After
        # so believe it, rather than the supplied timestamp
        if self.consensus_valid_after is not None:
            self._append_consensus_timestamp_if_later(
                self.consensus_valid_after
                )
        elif timestamp:
            # Add the arg timestamp.
            self._append_consensus_timestamp_if_later(timestamp)
        # In any other case
        else:
            log.warning('Bad timestamp %s, using current time for consensus '
                        'timestamp update for relay %s',
                        timestamp, self.fingerprint)
            # Add the current datetime
            self._append_consensus_timestamp_if_later(
                datetime.utcnow().replace(microsecond=0))

    def _remove_old_consensus_timestamps(
            self, measurements_period=MEASUREMENTS_PERIOD):
        self._consensus_timestamps = \
            remove_old_consensus_timestamps(
                copy.deepcopy(self._consensus_timestamps), measurements_period
                )

    def update_consensus_timestamps(self, timestamp=None):
        self._add_consensus_timestamp(timestamp)
        self._remove_old_consensus_timestamps()

    @property
    def relay_in_recent_consensus_count(self):
        """Number of times the relay was in a conensus."""
        return len(self._consensus_timestamps)

    def can_exit_to_port(self, port):
        """
        Returns True if the relay has an exit policy and the policy accepts
        exiting to the given portself or False otherwise.
        """
        assert isinstance(port, int)
        # if dind't get the descriptor, there isn't exit policy
        # When the attribute is gotten in getattr(self._desc, "exit_policy"),
        # is possible that stem's _input_rules is None and raises an exception
        # (#29899):
        #   File "/usr/lib/python3/dist-packages/sbws/lib/relaylist.py", line 117, in can_exit_to_port  # noqa
        #     if not self.exit_policy:
        #   File "/usr/lib/python3/dist-packages/stem/exit_policy.py", line 512, in __len__  # noqa
        #     return len(self._get_rules())
        #   File "/usr/lib/python3/dist-packages/stem/exit_policy.py", line 464, in _get_rules  # noqa
        #     for rule in decompressed_rules:
        # TypeError: 'NoneType' object is not iterable
        # Therefore, catch the exception here.
        try:
            if self.exit_policy:
                return self.exit_policy.can_exit_to(port=port)
        except TypeError:
            return False
        return False

    def is_exit_not_bad_allowing_port(self, port):
        return (Flag.BADEXIT not in self.flags and
                Flag.EXIT in self.flags and
                self.can_exit_to_port(port))

    def increment_relay_recent_measurement_attempt_count(self):
        """
        Increment The number of times that a relay has been queued
        to be measured.

        It is call from :funf:`~sbws.core.scaner.main_loop`.
        """
        # If it was not in the previous measurements version, start counting
        if self.relay_recent_measurement_attempt_count is None:
            self.relay_recent_measurement_attempt_count = 0
        self.relay_recent_measurement_attempt_count += 1

    def increment_relay_recent_priority_list_count(self):
        """
        The number of times that a relay is "prioritized" to be measured.

        It is call from
        :meth:`~sbws.lib.relayprioritizer.RelayPrioritizer.best_priority`.
        """
        # If it was not in the previous measurements version, start counting
        if self.relay_recent_priority_list_count is None:
            self.relay_recent_priority_list_count = 0
        self.relay_recent_priority_list_count += 1



class RelayList:
    ''' Keeps a list of all relays in the current Tor network and updates it
    transparently in the background. Provides useful interfaces for getting
    only relays of a certain type.
    '''

    def __init__(self, args, conf, controller,
                 measurements_period=MEASUREMENTS_PERIOD, state=None):
        self._controller = controller
        self.rng = random.SystemRandom()
        self._refresh_lock = Lock()
        # To track all the consensus seen.
        self._consensus_timestamps = []
        # Initialize so that there's no error trying to access to it.
        # In future refactor, change to a dictionary, where the keys are
        # the relays' fingerprint.
        self._relays = []
        # The period of time for which the measurements are keep.
        self._measurements_period = measurements_period
        self._state = state
        # NOTE: blocking: writes to disk
        if self._state:
            if self._state.get('recent_measurement_attempt_count', None) \
                    is None:
                self._state['recent_measurement_attempt_count'] = 0
        self._refresh()

    def _need_refresh(self):
        # New consensuses happen every hour.
        return datetime.utcnow() >= \
            self.last_consensus_timestamp + timedelta(seconds=60*60)

    @property
    def last_consensus_timestamp(self):
        """Returns the datetime when the last consensus was obtained."""
        if (getattr(self, "_consensus_timestamps")
                and self._consensus_timestamps):
            return self._consensus_timestamps[-1]
        # If the object was not created from __init__, it won't have
        # consensus_timestamps attribute or it might be empty.
        # In this case force new update.
        # Anytime more than 1h in the past will be old.
        self._consensus_timestamps = []
        return datetime.utcnow() - timedelta(seconds=60*61)

    @property
    def relays(self):
        # See if we can get the list of relays without having to do a refresh,
        # which is expensive and blocks other threads
        if self._need_refresh():
            log.debug('We need to refresh our list of relays. '
                      'Going to wait for lock.')
            # Whelp we couldn't just get the list of relays because the list is
            # stale. Wait for the lock so we can refresh it.
            with self._refresh_lock:
                log.debug('We got the lock. Now to see if we still '
                          'need to refresh.')
                # Now we have the lock ... but wait! Maybe someone else already
                # did the refreshing. So check if it still needs refreshing. If
                # not, we can do nothing.
                if self._need_refresh():
                    log.debug('Yup we need to refresh our relays. Doing so.')
                    self._refresh()
                else:
                    log.debug('No we don\'t need to refresh our relays. '
                              'It was done by someone else.')
            log.debug('Giving back the lock for refreshing relays.')
        return self._relays

    @property
    def fast(self):
        return self._relays_with_flag(Flag.FAST)

    @property
    def exits(self):
        return self._relays_with_flag(Flag.EXIT)

    @property
    def bad_exits(self):
        return self._relays_with_flag(Flag.BADEXIT)

    @property
    def non_exits(self):
        return self._relays_without_flag(Flag.EXIT)

    @property
    def guards(self):
        return self._relays_with_flag(Flag.GUARD)

    @property
    def authorities(self):
        return self._relays_with_flag(Flag.AUTHORITY)

    @property
    def relays_fingerprints(self):
        # Using relays instead of _relays, so that the list get updated if
        # needed, since this method is used to know which fingerprints are in
        # the consensus.
        return [r.fingerprint for r in self.relays]

    def random_relay(self):
        return self.rng.choice(self.relays)

    def _relays_with_flag(self, flag):
        return [r for r in self.relays if flag in r.flags]

    def _relays_without_flag(self, flag):
        return [r for r in self.relays if flag not in r.flags]

    def _remove_old_consensus_timestamps(self):
        self._consensus_timestamps = remove_old_consensus_timestamps(
            copy.deepcopy(self._consensus_timestamps),
            self._measurements_period
            )

    def _init_relays(self):
        """Returns a new list of relays that are in the current consensus.
        And update the consensus timestamp list with the current one.

        """
        c = self._controller
        # This will get router statuses from this Tor cache, might not be
        # updated with the network.
        # Change to stem.descriptor.remote in future refactor.
        network_statuses = c.get_network_statuses()
        new_relays_dict = dict([(r.fingerprint, r) for r in network_statuses])

        # Find the timestamp of the last consensus.
        timestamp = valid_after_from_network_statuses(network_statuses)
        self._consensus_timestamps.append(timestamp)
        self._remove_old_consensus_timestamps()
        # Update the relays that were in the previous consensus with the
        # new timestamp
        new_relays = []
        relays = copy.deepcopy(self._relays)
        for r in relays:
            if r.fingerprint in new_relays_dict.keys():
                r.update_consensus_timestamps(timestamp)
                new_relays_dict.pop(r.fingerprint)
                new_relays.append(r)

        # Add the relays that were not in the previous consensus
        # If there was an relay in some older previous consensus,
        # it won't get stored, so its previous consensuses are lost,
        # but probably this is fine for now to don't make it more complicated.
        for fp, ns in new_relays_dict.items():
            r = Relay(ns.fingerprint, c, ns=ns, timestamp=timestamp)
            new_relays.append(r)
        return new_relays

    def _refresh(self):
        # Set a new list of relays.
        self._relays = self._init_relays()

        log.info("Number of consensuses obtained in the last %s days: %s.",
                 int(self._measurements_period / 24 / 60 / 60),
                 self.recent_consensus_count)
        # NOTE: blocking, writes to file!
        if self._state is not None:
            self._state['recent_consensus_count'] = self.recent_consensus_count

    @property
    def recent_consensus_count(self):
        """Number of times a new consensus was obtained."""
        return len(self._consensus_timestamps)

    def exits_not_bad_allowing_port(self, port):
        return [r for r in self.exits
                if r.is_exit_not_bad_allowing_port(port)]

    def increment_recent_measurement_attempt_count(self):
        """
        Increment the number of times that any relay has been queued to be
        measured.

        It is call from :funf:`~sbws.core.scaner.main_loop`.

        It is read and stored in a ``state`` file.
        """
        # NOTE: blocking, writes to file!
        if self._state:
            self._state['recent_measurement_attempt_count'] += 1
