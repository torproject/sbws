# Readme

[![Build Status](https://travis-ci.org/pastly/simple-bw-scanner.svg?branch=master)](https://travis-ci.org/pastly/simple-bw-scanner)

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

The sbws documentation can be found at [Read the Docs](https://sbws.readthedocs.io)
and
[this onion service](http://d7pxflytfsmz6uh3x7i2jxzzwea6nbpmtsz5tmfkcin5edapaig5vpyd.onion/)
([v2](http://sdmb3rfvp3wadu6y.onion/)).

## Layout of the sbws repo

- `docs/` the source of the sbws documentation website.
- `sbws/` the source code for sbws.
- `sbws/core/` each file contains code specific to a single sbws command.
- `sbws/lib/` complex data structures and classes useful to one or more sbws
  commands. If you're making a new class, it probably belongs here.
- `sbws/util/` simplier, "make life easier" collections of functions.
- `scripts/maint/` scripts for **maint**aining sbws and doing administrative
  things like regenerating the website or updating the AUTHORS file.
- `scripts/tools/` misc. scripts for users of sbws.
- `tests/testnets/` scripts and code for running mini Tor networks locally and
  performing integration tests with them.
- `tests/` unit tests executed with `pytest` or `tox`.

### Build HTML documentation

    pip install -e .[doc]
    cd docs
    make html

The generated HTML will be in `docs/build/`.

## The `.sbws` directory

By default is `~/.sbws`. You can choose a different one by specifying `-d` when
calling sbws.

    sbws -d /tmp/testing-dotsbws init
    sbws -d /tmp/testing-dotsbws client

In this directory you will find

- `config.ini` The configuration file you should be editing if you want to
  modify sbws's behavior.
- `config.log.ini` The configuration file you should edit if you want to modify
  how sbws logs.
- `datadir` Once your sbws scanner has started gathering results, it will dump
  them into this directory. Other sbws commands (such as generate and stats)
  read results from the files in this directory.

## Running tests

Make sure you have test dependencies installed. From within the top level
repository directory:

    pip install -e .[test]

This should install tox and pytest. Then simply run `tox`.
