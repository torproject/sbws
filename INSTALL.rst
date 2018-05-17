.. _install:

Installing Simple Bandwidth Scanner
===================================

(At the time of writing) sbws depends on two Python libraries.

- Stem_
- Requests_

Sbws relies on a stem feature that is not planned to be in a tagged release
until stem 1.7.0.

Read all the information for the installation method of your choice before
beginning. Often you will want to be armed with the knowledge of the latest
released version of sbws. Determine that by examining its git tags, or visiting
its `release page`_. In the remainder of this document, we assume the latest
version is 1.5.3, which would be tagged as ``v1.5.3``.

.. _Stem: https://stem.torproject.org/
.. _Requests: http://docs.python-requests.org/

.. _release page: https://github.com/pastly/simple-bw-scanner/releases

Virtualenv - Production
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


Virtualenv - Development
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
