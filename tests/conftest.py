from tests.common import MockPastlyLogger
import pytest


@pytest.fixture(scope='module')
def log():
    pl = MockPastlyLogger()
    return pl
