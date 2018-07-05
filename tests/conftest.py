"""Common pytest configuration for unit and integration tests."""
import pytest
from sbws.util.parser import create_parser


@pytest.fixture(scope='session')
def parser():
    return create_parser()


@pytest.fixture()
def datadir(request):
    """get, read, open test files from the tests "data" directory."""
    class D:
        def __init__(self, basepath):
            self.basepath = basepath

        def open(self, name, mode="r"):
            return self.basepath.join(name).open(mode)

        def join(self, name):
            return self.basepath.join(name).strpath

        def read(self, name):
            with self.open(name, "r") as f:
                return f.read()

        def readlines(self, name):
            with self.open(name, "r") as f:
                return f.readlines()
    return D(request.fspath.dirpath("data"))
