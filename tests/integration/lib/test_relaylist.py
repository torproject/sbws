from sbws.lib.relaylist import Relay


def test_relay_properties(persistent_launch_tor):
    cont = persistent_launch_tor
    # AA45C13025C037F056E734169891878ED0880231 is auth1
    fp = 'AA45C13025C037F056E734169891878ED0880231'
    relay = Relay(fp, cont)
    assert relay.nickname == 'auth1'
    assert relay.fingerprint == 'AA45C13025C037F056E734169891878ED0880231'
    assert 'Authority' in relay.flags
    assert not relay.exit_policy or not relay.exit_policy.is_exiting_allowed()
    print(relay)
    assert relay.average_bandwidth == 1073741824
    assert relay.bandwidth == 0
    assert relay.address == '127.10.0.1'
    assert relay.master_key_ed25519 == \
        'wLglSEw9/DHfpNrlrqjVRSnGLVWfnm0vYxkryH4aT6Q'
