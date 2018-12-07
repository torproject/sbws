import sbws.util.stem as stem_utils


def test_launch_and_okay(persistent_launch_tor):
    cont = persistent_launch_tor
    assert stem_utils.is_bootstrapped(cont)


def test_set_torrc_runtime_option_succesful(persistent_launch_tor):
    controller = persistent_launch_tor
    runtime_options = controller.get_conf_map(['__LeaveStreamsUnattached'])
    assert runtime_options == {'__LeaveStreamsUnattached': ['1']}


def test_set_torrc_runtime_invalidrequest_option_fail(persistent_launch_tor):
    controller = persistent_launch_tor
    try:
        controller.set_conf('ControlSocket', '/tmp/dummy')
    except stem_utils.InvalidRequest as e:
        assert "Unable to set option" in e.message
