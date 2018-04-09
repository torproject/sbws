import pytest


class MockPastlyLogger:
    def __init__(self, *a, _do_print=False, **kw):
        self._logged_lines = []
        self._do_print = _do_print
        pass

    def debug(self, *s):
        self._logged_lines.append(' '.join(str(_) for _ in s))
        if self._do_print:
            print(*s)

    def info(self, *s):
        return self.debug(*s)

    def notice(self, *s):
        return self.info(*s)

    def warn(self, *s):
        return self.notice(*s)

    def error(self, *s):
        return self.warn(*s)

    def test_get_logged_lines(self, clear=True):
        for line in self._logged_lines:
            yield line
        if clear:
            self._logged_lines = []


@pytest.fixture(scope='module')
def log():
    pl = MockPastlyLogger()
    return pl
