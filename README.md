# Readme

It doesn't get simplier than this, folks.

Run `sbws server` on the same machine as a relay with an exit policy that
allows exiting to itself on a single port. (Notice: it won't get the exit flag)

Run `sbws client` on a well-connected machine on the Internet.

The scanner builds two hop circuits consisting of the relay being measured and
the helper relay running server.py. Over these circuits it measures RTT and
download performance.

## Boring things

This project follows [semantic versioning][] and thus every major version has
the potential for breaking changes. You can find information about what those
are at the following places.

- In [`CHANGELOG.md`](/CHANGELOG.md)

[semantic versioning]: https://semver.org/

In addition to the overall semantic version for sbws as a whole, there are
simple integer versions for (i) the protcol sbws clients and servers use to
speak to each other, and (ii) the format in which results are stored.
Incrementing either of these version numbers requires a major version change
for sbws. (Note that the reverse is **not** true: a major sbws version change
does not require the integer versions for the wire protocol or result format to
change)

This project is released to the public domain under the CC0 1.0 Universal
license. See [`LICENSE.md`](/LICENSE.md) for more information.

## Installing

Clone the repo

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install .
    sbws init
    sbws client -h
    sbws server -h

## Authenticating to `sbws server`

**XXX Write this.**

## Documentation

See more documentation in [/docs/source/](/docs/source/)

## Configuration

Sbws has two config files it reads.

It first reads the config file containing the default values for almost all
options. If you installed sbws in a virtual environment located at /tmp/venv, then
you will probably find the `config.default.ini` in a place such as
`/tmp/venv/lib/python3.5/site-packages/sbws/`
**You should never edit this file**. You can also click on
[this link](/sbws/config.default.ini) to see the default config file if you're
reading this on GitHub.

Sbws then reads your custom config file. By default, after running `sbws init`,
it is located in `~/.sbws/config.ini`. A configuration option in this file
overwrites the default file found in the default file.

**No other configuration files are read.** The only files that are read are the
`config.default.ini` file located in a place the user shouldn't touch, and the
`config.ini` in their `.sbws` directory.

## The `.sbws` directory

By default is `~/.sbws`. You can choose a different one by specifying `-d` when
calling sbws.

    sbws -d /tmp/testing-dotsbws init
    sbws -d /tmp/testing-dotsbws client

In this directory you will find

- `config.ini` The configuration file you should be editing if you want to
  modify sbws's behavior.
- `datadir` Once your sbws client has started gathering results, it will dump
  them into this directory. Other sbws commands (such as generate and stats)
  read results from the files in this directory.

## Build HTML documentation

    pip install -e .[doc]
    cd docs
    make html

The generated HTML will be in [/docs/build/](/docs/build/)

## Running tests

Make sure you have test dependencies installed. From within the top level
repository directory:

    pip install -e .[test]

This should install tox and pytest.

Since my development environment has Python 3.5 and tox is only configured to
test 3.5, both the `tox` and `pytest` commands have the same result. Once sbws
gets properly open source, Travis should run tox with a variety of Python 3.X
versions.

To run the tests, run `pytest`. To generate HTML output of test coverage, run
`pytest --cov --cov-report=html`. A `htmlcov` directory will be created in
current working directory. Open it in a web browser and prepare to be amazed.
It will highlight (un)covered lines! How cool is that?!
