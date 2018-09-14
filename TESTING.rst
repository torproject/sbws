.. _testing:

Installing tests dependencies and running tests
==================================================

To run the tests, extra Python depenencies are needed:

- Flake8_
- tox_
- pytest_
- coverage_

To install them from ``sbws`` ::

    pip install .[dev] && pip install .[test]

To run the tests::

    tox
