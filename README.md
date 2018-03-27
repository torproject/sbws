# simple-bw-scanner

It doesn't get simplier than this, folks.

Run `sbws server` on the same machine as a relay with an exit policy that
allows exiting to itself on a single port. (Notice: it won't get the exit flag)

Run `sbws client` on a well-connected machine on the Internet.

The scanner builds two hop circuits consisting of the relay being measured and
the helper relay running server.py. Over these circuits it measures RTT and
download performance.

# Installing

Clone the repo

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install .
    sbws init
    sbws client -h
    sbws server -h

# Authenticating to `sbws server`

Generate a password and store in passwords.txt. It must be 64 characters (or
bytes?) long and valid unicode. Just use regular ASCII 1-byte chars, as in this
example please. Multiple passwords may be specified, one per line.

    (</dev/urandom tr -dc 'a-zA-Z0-9' | head -c 64; echo '') | tee -a passwords.txt

The client will pick the first password and use it always. The server will
accept any password in the file.

----------

**lib/circuitbuilder.py** Only one subclass of CircuitBuilder is used as of
this writing, and that is GapsCircuitBuilder. Oddly enough, there are no gaps
in the circuits we ask it to build.

# Documentation

See more documentation in [/docs/source/](/docs/source/)

## Build HTML documentation

    pip install -e .[doc]
    cd docs
    make html

The generated HTML will be in [/docs/build/](/docs/build/)
