import sbws.util.stem as stem_utils
from stem.descriptor.router_status_entry import RouterStatusEntryV3


def test_foo(persistent_launch_tor):
    cont = persistent_launch_tor
    assert stem_utils.is_controller_okay(cont)
    assert stem_utils.is_bootstrapped(cont)


def test_get_relay_from_fp(persistent_launch_tor):
    cont = persistent_launch_tor
    # AA45C13025C037F056E734169891878ED0880231 is auth1
    relay = stem_utils.fp_or_nick_to_relay(
        cont, 'AA45C13025C037F056E734169891878ED0880231')
    assert isinstance(relay, RouterStatusEntryV3)
    assert relay.fingerprint == 'AA45C13025C037F056E734169891878ED0880231'
    assert relay.nickname == 'auth1'


def test_get_relay_from_nick(persistent_launch_tor):
    cont = persistent_launch_tor
    # AA45C13025C037F056E734169891878ED0880231 is auth1
    relay = stem_utils.fp_or_nick_to_relay(cont, 'auth1')
    assert isinstance(relay, RouterStatusEntryV3)
    assert relay.fingerprint == 'AA45C13025C037F056E734169891878ED0880231'
    assert relay.nickname == 'auth1'
