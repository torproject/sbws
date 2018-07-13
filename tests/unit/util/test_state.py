from sbws.util.state import State
import os
# from tempfile import NamedTemporaryFile as NTF


def test_state_set_allowed_key_types(tmpdir):
    state = State(os.path.join(tmpdir, 'statefoo'))
    attempt_keys = ('k')
    for key in attempt_keys:
        state[key] = 4
        assert state[key] == 4


def test_state_set_bad_key_types(tmpdir):
    state = State(os.path.join(tmpdir, 'statefoo'))
    attempt_keys = (15983, None, True, -1.2, [], {}, set())
    for key in attempt_keys:
        try:
            state[key] = 4
        except TypeError:
            pass
        else:
            assert None, 'Should not have been able to use %s %s as a key' %\
                (key, type(key))
    try:
        state[key]
    except TypeError:
        pass
    else:
        assert None, '%s %s is not a valid key type, so should have got '\
            'TypeError when giving it' % (key, type(key))


def test_state_set_allowed_value_types(tmpdir):
    state = State(os.path.join(tmpdir, 'statefoo'))
    attempt_vals = (15983, None, True, -1.2, 'loooooool')
    for val in attempt_vals:
        state['foo'] = val
        assert state['foo'] == val


def test_state_set_bad_value_types(tmpdir):
    state = State(os.path.join(tmpdir, 'statefoo'))
    attempt_vals = ([], {}, set())
    for val in attempt_vals:
        try:
            state['foo'] = val
        except TypeError:
            pass
        else:
            assert None, 'Should not have been able to use %s %s as a value' %\
                (val, type(val))


def test_state_del(tmpdir):
    state = State(os.path.join(tmpdir, 'statefoo'))
    d = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    for key in d:
        state[key] = d[key]
    assert len(state) == len(d)

    del d['a']
    del state['a']
    assert len(state) == len(d)
    for key in d:
        assert d[key] == state[key]

    attempt_keys = (15983, None, True, -1.2, [], {}, set())
    for key in attempt_keys:
        try:
            del state[False]
        except TypeError:
            pass
        else:
            assert None, 'Should not have been allowed to delete %s %s '\
                'because it is not a valid key type' % (key, type(key))

    d['e'] = 5
    state['e'] = 5
    d['e'] = 5.5
    state['e'] = 5.5
    assert len(state) == len(d)


def test_state_get_len(tmpdir):
    state = State(os.path.join(tmpdir, 'statefoo'))
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
    state = State(os.path.join(tmpdir, 'statefoo'))
    d = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    for key in d:
        state[key] = d[key]
    assert 'a' in state
    assert 'e' not in state


def test_state_iter(tmpdir):
    state = State(os.path.join(tmpdir, 'statefoo'))
    for key in state:
        pass
    d = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    for key in d:
        state[key] = d[key]
    for key in state:
        pass
