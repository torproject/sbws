.. _install:

Installing Simple Bandwidth Scanner
-----------------------------------

First, clone the repo. Then

::

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install .  # if this is for deployment
    pip install -e .[test]  # if this is for development or testing
    sbws init
    sbws client -h
    sbws server -h

Make sure the sbws commands complete without error.
