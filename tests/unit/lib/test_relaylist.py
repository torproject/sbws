from sbws.lib.relaylist import RelayList


def test_relaylist_master_key_ed25519(start_tor):
    # This test starts tor, so it is slow. And it will fail whenever there are
    # network problems
    controller = start_tor
    rl = RelayList(None, None, controller)
    relay = [r for r in rl.relays if r.nickname == 'moria1'][0]
    assert relay.fingerprint == '9695DFC35FFEB861329B9F1AB04C46397020CE31'
    assert relay.identifier is None
    assert relay.master_key_ed25519 == \
        'yp0fwtp4aa/VMyZJGz8vN7Km3zYet1YBZwqZEk1CwHI'
