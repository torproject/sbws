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
=======
`sbws` will be considered production ready when version 1.0.0 will be releases.

More extensive documentation can be found in the ./docs directory,
also online at https://sbws.readthedocs.io and
[this onion service](http://d7pxflytfsmz6uh3x7i2jxzzwea6nbpmtsz5tmfkcin5edapaig5vpyd.onion/)
([v2](http://sdmb3rfvp3wadu6y.onion/)).

## Layout of `sbws` source code directory

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
