.. _install:

Installing Simple Bandwidth Scanner
===================================

The prefered method to install ``sbws`` is to install it from your system
distribution.
Currently there is not any system distribution package.
In the meanwhile, follow the following steps.

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

::

    pip install ../stem

Install sbws and its remaining dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here is where you might want to know what the latest release of sbws is (this
document assumes it is 1.5.3). Skip
the ``git checkout`` if you want to run the bleeding edge tip-of-master version
of sbws.

::

    git checkout v1.5.3
    pip install .

Run sbws
~~~~~~~~~~

If you would like to use a custom configuration file you can create it in
``~/.sbws.ini`` or provide ``sbws`` with it via ``-c`` ``--config`` option.

See the documentation section about configuration files for more information
about how to create a configuration file.

Tor run the scanner run
::

    sbws scanner


[OBSOLETE DO NOT FOLLOW] Virtualenv - Production
------------------------------------------------------------------------------

Installing
~~~~~~~~~~

::

    git clone https://github.com/pastly/simple-bw-scanner.git
    cd simple-bw-scanner
    git checkout v1.5.3
    virtualenv -p python3 venv
    source venv/bin/activate
    pip install --process-dependency-links .
    sbws init

.. note::

    Because we relay on a ``-dev`` version of stem, we need to fetch it from
    git.torproject.org. Thus ``--process-dependency-links`` is necessary.

.. warning::

    Run these commands one at a time and check for errors before continuing.

Updating
~~~~~~~~

::

    cd simple-bw-scanner
    git pull
    # Determine the newest released version. Assuming it is v1.5.3 ...
    git checkout v1.5.3
    source venv/bin/activate
    pip install --process-dependency-links --upgrade-strategy eager --upgrade .


[OBSOLETE DO NOT FOLLOW] Virtualenv - Development
------------------------------------------------------------------------------

These are almost exactly the same. The difference is the pip command: we
install sbws in an editable state so we don't have to re-run pip every time we
make a change.

::

    git clone https://github.com/pastly/simple-bw-scanner.git
    cd simple-bw-scanner
    git checkout v1.5.3
    virtualenv -p python3 venv-editable
    source venv-editable/bin/activate
    pip install --process-dependency-links --editable .
    sbws init

.. note::

    Because we relay on a ``-dev`` version of stem, we need to fetch it from
    git.torproject.org. Thus ``--process-dependency-links`` is necessary.

.. warning::

    Run these commands one at a time and check for errors before continuing.

Updating
~~~~~~~~

::

    cd simple-bw-scanner
    git pull
    # Determine the newest released version. Assuming it is v1.5.3 ...
    git checkout v1.5.3

.. todo::

    This doesn't update dependencies and needs to be fixed.
