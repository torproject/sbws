class MockPastlyLogger:
    def __init__(self, *a, **kw):
        pass

    def debug(self, *s):
        print(*s)

    def info(self, *s):
        return self.debug(*s)

    def notice(self, *s):
        return self.info(*s)

    def warn(self, *s):
        return self.notice(*s)

    def error(self, *s):
        return self.warn(*s)
