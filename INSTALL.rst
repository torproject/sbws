.. _install:

Installing Simple Bandwidth Scanner
===================================

The prefered method to install ``sbws`` is to install it from your system
distribution.
Currently there is not any system distribution package.
In the meantime, follow the following steps.

System requirements
--------------------

- Tor
- Python 3
- virtualenv_ (while there is not ``stem`` release > 1.6.0, it is
  recommended to install the required python dependencies in a virtualenv)

In Debian::

    sudo apt install tor python3 virtualenv

Python dependencies
--------------------

- Stem_ > 1.6.0
- Requests_ (with socks_ support) >= 2.10.0

To install the Python dependencies, create a ``virtualenv`` first

::

    virtualenv venv -p /usr/bin/python3
    source venv/bin/activate

Clone ``sbws``::

    git clone https://gitweb.torproject.org/sbws.git

Install the python dependencies::

    cd sbws && pip install --process-dependency-links .

.. note:: ``process-dependency-links`` will clone ``stem`` from master and
   install it. It's deprecated, but it won't be needed as soon as there is
   an ``stem`` release > 1.6.0

``sbws`` needs :term:`destination` s to request files from.
Please, see :ref:`deploy` to know how to configure, deploy and run ``sbws``.

Installing tests dependencies and running them
------------------------------------------------

To run the tests, extra Python depenencies are needed:

- Flake8_
- tox_
- pytest_
- coverage_

To install them from ``sbws`` ::

    pip install .[dev] && pip install .[test]

To run the tests::

    tox


Installing documentation dependendencies and building it
---------------------------------------------------------

To build the documentation, extra Python dependencies are needed:

- Sphinx_
- recommonmark_
- Pylint_ (only to update the diagrams)

To install them from ``sbws``::

    pip install .[doc]

To build the documentation as HTML::

    cd docs/ && make html

The generated HTML will be in ``docs/build/``.

To build the manual (``man``) pages::

    cd docs/ && make man

The generated man pages will be in ``docs/man/``.

To build the documentation diagrams::

    cd docs/ && make umlsvg

The generated diagrams will be in ``docs/build/images/``.

.. _virtualenv: https://virtualenv.pypa.io/en/stable/installation/
.. _Stem: https://stem.torproject.org/
.. _socks: http://docs.python-requests.org/en/master/user/advanced/#socks
.. _Requests: http://docs.python-requests.org/
.. _Flake8: http://flake8.pycqa.org/
.. _pytest: https://docs.pytest.org/
.. _tox: https://tox.readthedocs.io
.. _Coverage: https://coverage.readthedocs.io/
.. _Sphinx: http://www.sphinx-doc.org
.. _recommonmark: https://recommonmark.readthedocs.io/
.. _Pylint: https://www.pylint.org/
