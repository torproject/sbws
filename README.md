Readme
======

[![Build Status](https://travis-ci.org/torproject/sbws.svg?branch=master)](https://travis-ci.org/https://travis-ci.org/torproject/sbws)

Simple Bandwidth Scanner (called `sbws`) is a Tor bandwidth scanner that
generates bandwidth files to be used by Directory Authorities.

The scanner measures the bandwidth of each relay in the Tor network
(except the directory authorities) by creating a two hops circuit
with the relay. It then measures the bandwidth by downloading data
from a destination Web Server and stores the measurements.

The generator read the measurements, aggregates, filters and
scales them using torflow's scaling method.
Then it generates a bandwidth list file that is read
by a directory authority to report relays’ bandwidth in its vote.

**WARNING**: This software is intended to be run by researchers using a test
Tor network, such as chutney or shadow, or by the Tor bandwidth authorities
on the public Tor network.
Please do not run this software on the public Tor network unless you are one
of the Tor bandwidth authorities, to avoid creating unnecessary traffic.

**ADVICE**: It is recommended to read this documentation at
[Read the Docs](https://sbws.rtfd.io). In
[Tor Project Gitlab](https://gitlab.torproject.org/tpo/network-health/sbws)
(tpo Gitlab) some links won't be properly rendered.
It can also be read after installing the Debian package ``sbws-doc`` in
``/usr/share/doc/sbws`` or after building it locally as explained in
``./docs/source/documenting.rst``.


Installing
------------

See [./INSTALL.rst](INSTALL.rst) (in local directory or tpo Gitlab) or
[INSTALL.html](INSTALL.html) (local build or Read the Docs).

Deploying and running
---------------------

See [./DEPLOY.rst](DEPLOY.rst) (in local directory or tpo Gitlab) or
[DEPLOY.html](DEPLOY.html) (local build or Read the Docs).

Changelog
--------------

See [./CHANGELOG.rst](CHANGELOG.rst) (in local directory or tpo Gitlab) or
[CHANGELOG.html](CHANGELOG.html)  (local build or Read the Docs).

Documentation
--------------

More extensive documentation can be found in the ``./docs`` directory,
and online at [sbws.rtfd.io](https://sbws.readthedocs.io).

## License

This work is in the public domain within the United States.

We waive copyright and related rights in the work worldwide through the
[CC0-1.0 license](https://creativecommons.org/publicdomain/zero/1.0).

You can find a copy of the CC0 Public Domain Dedication along with this
software in ./LICENSE.md

## Authors

See [./AUTHORS.md](AUTHORS.md) (in local directory or tpo Gitlab) or
[AUTHORS.html](AUTHORS.html) (local build or Read the Docs).
