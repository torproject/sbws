

def test_relay_properties(rl):
    relay = [relay for relay in rl.relays if relay.nickname == 'test000a'][0]
    # The fingerprint and the master key can't be tested cause they are
    # created by chutney.
    assert 'Authority' in relay.flags
    assert not relay.exit_policy or not relay.exit_policy.is_exiting_allowed()
    assert relay.average_bandwidth == 1073741824
    assert relay.consensus_bandwidth == 0
    assert relay.address == '127.0.0.1'


def test_relay_list_last_consensus_timestamp(rl):
    assert rl.last_consensus_timestamp == \
        rl._relays[0].last_consensus_timestamp
