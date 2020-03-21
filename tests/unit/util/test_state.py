from sbws.util.state import State
import os
# from tempfile import NamedTemporaryFile as NTF


def test_state_set_allowed_key_types(tmpdir):
    state = State(os.path.join(str(tmpdir), 'statefoo'))
    attempt_keys = ('k')
    for key in attempt_keys:
        state[key] = 4
        assert state[key] == 4


def test_state_set_allowed_value_types(tmpdir):
    state = State(os.path.join(str(tmpdir), 'statefoo'))
    attempt_vals = (15983, None, True, -1.2, 'loooooool')
    for val in attempt_vals:
        state['foo'] = val
        assert state['foo'] == val


def test_state_del(tmpdir):
    state = State(os.path.join(str(tmpdir), 'statefoo'))
    d = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    for key in d:
        state[key] = d[key]
    assert len(state) == len(d)

    del d['a']
    del state['a']
    assert len(state) == len(d)
    for key in d:
        assert d[key] == state[key]

    d['e'] = 5
    state['e'] = 5
    d['e'] = 5.5
    state['e'] = 5.5
    assert len(state) == len(d)


def test_state_get_len(tmpdir):
    state = State(os.path.join(str(tmpdir), 'statefoo'))
    d = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    for key in d:
        state[key] = d[key]
    assert len(state) == len(d)

    del d['a']
    del state['a']
    assert len(state) == len(d)

    d['e'] = 5
    state['e'] = 5
    d['e'] = 5.5
    state['e'] = 5.5
    assert len(state) == len(d)


def test_state_contains(tmpdir):
    state = State(os.path.join(str(tmpdir), 'statefoo'))
    d = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    for key in d:
        state[key] = d[key]
    assert 'a' in state
    assert 'e' not in state


def test_state_iter(tmpdir):
    state = State(os.path.join(str(tmpdir), 'statefoo'))
    for key in state:
        pass
    d = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    for key in d:
        state[key] = d[key]
    assert set([key for key in state]) == set(d)


def test_two_instances(tmpdir):
    """Test that 2 different intances don't overwrite each other"""
    s1 = State(os.path.join(str(tmpdir), 'state.dat'))
    s2 = State(os.path.join(str(tmpdir), 'state.dat'))
    s1["x"] = "foo"
    s2["y"] = "bar"
    assert s2["x"] == "foo"


def test_datetime_values(tmpdir):
    import datetime
    state = State(os.path.join(str(tmpdir), 'state.dat'))
    now = datetime.datetime.utcnow().replace(microsecond=0)
    state["datetimes"] = now
    assert now == state["datetimes"]
