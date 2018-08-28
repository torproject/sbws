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


.. _Stem: https://stem.torproject.org/
.. _Requests: http://docs.python-requests.org/

.. _release page: https://github.com/pastly/simple-bw-scanner/releases

Virtualenv - Development
------------------------------------------------------------------------------

Choose a directory to store code in. I might choose ``~/src``.

::

    cd ~/src

Get stem
~~~~~~~~~~~~~

::

    git clone https://git.torproject.org/stem.git

Get sbws
~~~~~~~~~~~~~~~~~

::

    git clone https://github.com/pastly/simple-bw-scanner.git
    cd simple-bw-scanner


Create and enter virtualenv
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

I like to keep mine in my simple-bw-scanner directory and assume that's where
you'll put it.

::

    virtualenv -p python3 venv
    source venv/bin/activate

Install stem in virtualenv
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sbws requires on features not yet in a released version of stem (1.7.0 has not
been released as of the time of writing). You can either install from the
master branch, or checkout ``60f034ad8b9c3aa48e7e2ecb0a2e159b6ed5bc71`` or
newer.

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
