# Readme

[![Build Status](https://travis-ci.org/pastly/simple-bw-scanner.svg?branch=master)](https://travis-ci.org/pastly/simple-bw-scanner)

`simple-bw-scanner` (also called `sbws`) is a Tor bandwidth scanner that
produces bandwidth measurements files to be used by Directory Authorities.

The scanner builds two hop circuits consisting of the relay being measured and
a fast exit. Over these circuits it measures RTT and bandwidth.

**WARNING**: This software is *only* intended to be run by Tor directory
authorities or researches using a test Tor network, chutney or shadow.
Please, do not run this software otherwise, since the measurements would not be
used by Tor and would only create more traffic in the Tor network.

See ./INSTALL.rst) for install instructions,
[./DEPLOY.rst](./DEPLOY.rst) for deploy instructions,
[./CONTRIBUTING](./CONTRIBUTING.rst) for contribution guidelines.

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
  performing tests with them.
- `tests/unit/` simple little tests that don't require Tor to be running
- `tests/integration/` more complex tests and/or tests that require Tor to be running
- `tests/testnets/` scripts and code for running mini Tor networks locally

## Boring things

### Versioning

This project follows [semantic versioning][] and thus every major version has
the potential for breaking changes. You can find information about what those
are at the following places.

- In the CHANGELOG

[semantic versioning]: https://semver.org/

In addition to the overall semantic version for sbws as a whole, there is a
simple integer version for the format in which results are stored.
Incrementing this integer requires a major version change for sbws. (Note that
the reverse is **not** true: a major sbws version change does not require the
integer version for the result format to change)

**Note**: In semantic versioning, "3.4.1-dev" comes **before** "3.4.1". With
this in mind and assuming the current version is "3.4.1-dev": in the last few
commits leading up to a new release, the version will be updated to

- "3.4.1" if only bug fixes
- "3.5.0" if bug fixes and/or backwards-compatible additions/changes
- "4.0.0" if bug fixes and/or backwards-compatible additions/changes and/or
  backwards-**in**compatible additions/changes

Say the version is updated to "3.5.0". The commit **immediately** after the
tagged release should update the version to "3.5.1-dev".

**Note**: Before version 1.0.0, we will make an effort to follow semver with a
prepended "0.". For example, "0.2.3" to "0.3.0" probably had a major breaking
change. However, we don't promise this will be followed well. Only trust the
semantic meaning of version numbers when they have reached 1.0.0. Don't worry,
we'll be 1.0.0 before we expect a full deployment on the real Tor network.
(Oh god please don't make me eat my words).

To the best of my knowledge, everything said in this section except our
conventions regarding version bump commit timing is standard semantic
versioning and spelled out in the [link above][semantic versioning].

### The public API for sbws

As required by semantic versioning, the public API for sbws will not change
without a major version bump. The public API is

- **The available configuration options and their defaults**. New options may
  be added without a major version bump, but no options will be removed, nor
will defaults be drastically changed. Examples of drastic changes to defaults
include obvious things like changing the default URL for the file to download
or a location for data storage, but also more subjective things, such as
increasing the target download time significantly (6s to 60s). Examples of an
insignificant change include changing the default client nickname. Rule of
thumb: if it is likely to affect results or sbws behavior significantly, it is
a major change.

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

- **NOT the name, location, signature, or existance of python functions**. Sbws
  is meant to be ran as a standalone program. It is not at all meant to be
treated or used like a library. Users of sbws do *not* need an understanding of
how its code is laid out. Therefore the code may change drastically without a
major version bump as long as the way users interact with it does not change in
a backward incompatible way.

## The `.sbws` directory

By default is `~/.sbws`.

In this directory you will find

- `datadir/` Once your sbws scanner has started gathering results, it will dump
  them into this directory. Other sbws commands (such as generate and stats)
  read results from the files in this directory.
- `log/` If configured, this directory stores logs generated by all the sbws
  commands in rotating log files.
- `v3bw/` This directory stores the v3bw files created with `sbws generate`.
- `state.dat` A file for storing state needed between sbws commands. See its
  documentation for more information.
