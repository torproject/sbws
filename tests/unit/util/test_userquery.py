from unittest.mock import patch
from sbws.util.userquery import query_yes_no


@patch('builtins.input')
def test_userquery_missing_default_invalid_response(input_mock):
    input_mock.side_effect = [''] * 100 + ['k'] * 100 + ['yess'] * 100 +\
        ['no o'] * 100
    try:
        query_yes_no('a?', default=None)
    except StopIteration:
        pass
    else:
        assert None, 'Should have looped forever (and StopItration been '\
            'thrown when we stopped feeding it empty responses)'
    assert input_mock.call_count == 401


@patch('builtins.input')
def test_userquery_missing_default_yes_response(input_mock):
    input_mock.side_effect = [''] * 100 + ['y']
    assert query_yes_no('a?', default=None)
    assert input_mock.call_count == 101
    input_mock.reset_mock()

    input_mock.side_effect = [''] * 100 + ['Y']
    assert query_yes_no('a?', default=None)
    assert input_mock.call_count == 101
    input_mock.reset_mock()

    input_mock.side_effect = [''] * 100 + ['Yes']
    assert query_yes_no('a?', default=None)
    assert input_mock.call_count == 101
    input_mock.reset_mock()

    input_mock.side_effect = ['k'] * 100 + ['Yes']
    assert query_yes_no('a?', default=None)
    assert input_mock.call_count == 101
    input_mock.reset_mock()

    input_mock.side_effect = ['k'] * 100 + ['Yes', 'No']
    assert query_yes_no('a?', default=None)
    assert input_mock.call_count == 101
    input_mock.reset_mock()


@patch('builtins.input')
def test_userquery_missing_default_no_response(input_mock):
    input_mock.side_effect = [''] * 100 + ['n']
    assert not query_yes_no('a?', default=None)
    assert input_mock.call_count == 101
    input_mock.reset_mock()

    input_mock.side_effect = [''] * 100 + ['N']
    assert not query_yes_no('a?', default=None)
    assert input_mock.call_count == 101
    input_mock.reset_mock()

    input_mock.side_effect = [''] * 100 + ['No']
    assert not query_yes_no('a?', default=None)
    assert input_mock.call_count == 101
    input_mock.reset_mock()

    input_mock.side_effect = ['k'] * 100 + ['No']
    assert not query_yes_no('a?', default=None)
    assert input_mock.call_count == 101
    input_mock.reset_mock()

    input_mock.side_effect = ['k'] * 100 + ['No', 'Yes']
    assert not query_yes_no('a?', default=None)
    assert input_mock.call_count == 101
    input_mock.reset_mock()


@patch('builtins.input')
def test_userquery_yes_default_invalid_response(input_mock):
    input_mock.side_effect = [''] * 100
    assert query_yes_no('a?', default='yes')
    assert input_mock.call_count == 1


@patch('builtins.input')
def test_userquery_no_default_invalid_response(input_mock):
    input_mock.side_effect = [''] * 100
    assert not query_yes_no('a?', default='no')
    assert input_mock.call_count == 1


@patch('builtins.input')
def test_userquery_bad_default_invalid_response(input_mock):
    input_mock.side_effect = [''] * 100
    try:
        query_yes_no('a?', default='nooo')
    except ValueError:
        pass
    else:
        assert None, 'Should not have allowed us to specify a bad default '\
            'value'
    assert input_mock.call_count == 0
