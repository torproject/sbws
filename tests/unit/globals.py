def incrementing_time(start=2000, increment=1):
    while True:
        yield start
        start += increment


def monotonic_time(start=2000):
    return incrementing_time(start, increment=0.000001)


def static_time(value):
    while True:
        yield value
