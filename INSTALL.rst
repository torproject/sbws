.. _install:

Installing Simple Bandwidth Scanner
===================================

The recommended method  is to install it from your system package manager.

In Debian_/Ubuntu_ systems::

    sudo apt install sbws

To install also the documentation::

    sudo apt install sbws-doc

You might need to check in which releases is the package available.

There is a port_ for FreeBSD.

Continue reading to install ``sbws`` in other ways.

System requirements
--------------------

- Tor (last stable version is recommended)
- Python 3 (>= 3.6)

Python dependencies
--------------------

- Stem_ >= 1.7.0
- Requests_ (with socks_ support) >= 2.10.0

It is recommend to install the dependencies from your system package manager.
If that is not possible, because the Python dependencies are not available in
your system, you can install them from their sources.
We only recommend using pip_ for development or testing.

Installing sbws from source
---------------------------

Clone ``sbws``::

    git clone https://git.torproject.org/sbws.git
    git checkout maint-1.1

The branch ``maint-1.1`` is the last stable version and the one that should be
used in production.

and install it::

    cd sbws
    python3 setup.py install

Installing sbws for development or testing
------------------------------------------

If you use pip_, it is recommended to use virtualenv_, to avoid having
different versions of the same libraries in your system.

To create a ``virtualenv``::

    virtualenv venv -p /usr/bin/python3
    source venv/bin/activate

Clone ``sbws``::

    git clone https://git.torproject.org/sbws.git

Install the python dependencies::

    cd sbws && pip install -e .

Configuration and deployment
----------------------------

``sbws`` needs :term:`destination` s to request files from.

Please, see `<DEPLOY.rst>`_ (in the local directory or GitHub) or
`<DEPLOY.html>`_ (local build or Read the Docs)
to configure, deploy and run ``sbws``.

System physical requirements
-----------------------------

- Bandwidth: at least 12.5MB/s (100 Mbit/s).
- Free RAM: at least 2GB
- Free disk: at least 3GB

``sbws`` and its dependencies need around 20MB of disk space.
After 90 days ``sbws`` data files use around 3GB.
If ``sbws`` is configured to log to files (by default will log to the
system log), it will need a maximum of 500MB.

It is recommended to set up an automatic disk space monitoring on ``sbws`` data
and log partitions.

Details about ``sbws`` data:

``sbws`` produces around 100MB of data a day.
By default raw results' files are compressed after 10 days and deleted after 90.
The bandwidth files are compressed after 7 days and deleted after 1.
After 90 days, the disk space used by the data will be aproximately 3GB.
It will not increase further.
If ``sbws`` is configured to log to files, logs will be rotated after they
are 10MB and it will keep 50 rotated log files.

.. _virtualenv: https://virtualenv.pypa.io/en/stable/installation/
.. _Stem: https://stem.torproject.org/
.. _socks: http://docs.python-requests.org/en/master/user/advanced/#socks
.. https://readthedocs.org/projects/requests/ redirect to this, but the
.. certificate of this signed by rtd
.. _Requests: http://docs.python-requests.org/
.. http://flake8.pycqa.org/ certificate is signed by rtf
.. _Flake8: https://flake8.readthedocs.org/
.. _pytest: https://docs.pytest.org/
.. _tox: https://tox.readthedocs.io
.. _Coverage: https://coverage.readthedocs.io/
.. _port: https://www.freshports.org/net/py-sbws/
.. _Debian: https://packages.debian.org/search?keywords=sbws&searchon=names&suite=all&section=all
.. _Ubuntu: https://packages.ubuntu.com/search?keywords=sbws&searchon=names&suite=all&section=all
.. _pip: https://pypi.org/project/pip/
