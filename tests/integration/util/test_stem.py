import sbws.util.stem as stem_utils


def test_launch_and_okay(persistent_launch_tor):
    cont = persistent_launch_tor
    assert stem_utils.is_controller_okay(cont)
    assert stem_utils.is_bootstrapped(cont)
