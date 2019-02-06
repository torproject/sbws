"""Integration tests for circutibuilder.py"""


def test_build_circuit(cb):
    # Path is empty
    path = []
    circuit_id, _ = cb.build_circuit(path)
    assert not circuit_id
    # Valid path, not valid exit
    path = ['117A456C911114076BEB4E757AC48B16CC0CCC5F',
            '270A861ABED22EC2B625198BCCD7B2B9DBFFC93A']
    circuit_id, _ = cb.build_circuit(path)
    assert not circuit_id
    # Valid path and relays
    # path with relay1mbyteMAB and exit1
    path = ['117A456C911114076BEB4E757AC48B16CC0CCC5F',
            '270A861ABED22EC2B625198BCCD7B2B9DBFFC93C']
    circuit_id, _ = cb.build_circuit(path)
    assert circuit_id
