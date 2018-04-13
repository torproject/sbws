# Readme

It doesn't get simpler than this, folks.

Run `sbws server` on the same machine as a relay with an exit policy that
allows exiting to itself on a single port. (Notice: it won't get the exit flag)

Run `sbws client` on a well-connected machine on the Internet.

The scanner builds two hop circuits consisting of the relay being measured and
the helper relay running server.py. Over these circuits it measures RTT and
download performance.

## Boring things

### Versioning

This project follows [semantic versioning][] and thus every major version has
the potential for breaking changes. You can find information about what those
are at the following places.

- In [`CHANGELOG.md`](/CHANGELOG.md)

[semantic versioning]: https://semver.org/

In addition to the overall semantic version for sbws as a whole, there are
simple integer versions for (i) the protocol sbws clients and servers use to
speak to each other, and (ii) the format in which results are stored.
Incrementing either of these version numbers requires a major version change
for sbws. (Note that the reverse is **not** true: a major sbws version change
does not require the integer versions for the wire protocol or result format to
change)

### The public API for sbws

As required by semantic versioning, the public API for sbws will not change
without a major version bump. The public API is

- **The available configuration options and their defaults**. New options may
  be added without a major version bump, but no options will be removed, nor
will defaults be drastically changed. Examples of drastic changes to defaults
include obvious things like flipping any boolean value or a location for data
storage, but also more subjective things, such as increasing the target
download time significantly (6s to 60s). Examples of an insignificant change
include changing the default client nickname. Rule of thumb: if it is likely to
affect results or sbws behavior significantly, it is a major change.

- **The name and function of commands**. The command you run to perform certain
  actions will not change in a backward incompatible way without a major
version change. For example to generate a v3bw file you will always run `sbws
generate` unless there is a major version bump and the release notes indicate
the command has changed.

- **The format of output**. Results (stored in `~/.sbws/datadir` by default)
  will not change their format in a backward incompatible way without both a
major version bump and a bump in the result version integer. The v3bw file
generated with `sbws generate` will not change its format without a major
version bump. *Log lines and the output of `sbws stats` are exceptions to this
rule*.

- **The wire protocol**. The way `sbws client` and `sbws server` speak will not
  change in a backward incompatible way without both a major version bump and a
bump in the wire protocol version integer.

- **NOT the name, location, signature, or existance of python functions**. Sbws
  is meant to be ran as a standalone program. It is not at all meant to be
treated or used like a library. Users of sbws do *not* need an understanding of
how its code is laid out. Therefore the code may change drastically without a
major version bump as long as the way users interact with it does not change in
a backward incompatible way.

### License

This project is released to the public domain under the CC0 1.0 Universal
license. See [`LICENSE.md`](/LICENSE.md) for more information.

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
