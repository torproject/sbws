# Readme

[![Build Status](https://travis-ci.org/torproject/sbws.svg?branch=master)](https://travis-ci.org/https://travis-ci.org/torproject/sbws)

Simple Bandwidth Scanner (called `sbws`) is a Tor bandwidth scanner that
produces bandwidth measurements files to be used by Directory Authorities.

The scanner builds two hop circuits consisting of the relay being measured and
a fast exit. Over these circuits it measures RTT and bandwidth.

**WARNING**: This software is intended to be run by researchers using a test
Tor network, such as chutney or shadow, or by the Tor bandwidth authorities
on the public Tor network.
Please do not run this software on the public Tor network unless you are one
of the Tor bandwidth authorities, to avoid creating unnecessary traffic.

`sbws` will be considered production ready when version 1.0.0 will be released.

Installing
------------

See ./INSTALL.rst (or  [INSTALL](./INSTALL.rst) or [INSTALL](./INSTALL.html) )

Deploying and running
---------------------

See ./DEPLOY.rst (or  [DEPLOY](./DEPLOY.rst) or [DEPLOY](./DEPLOY.html) )

Contributing
--------------

See ./CONTRIBUTING.rst (or  [CONTRIBUTING](./CONTRIBUTING.rst) or
[CONTRIBUTING](./CONTRIBUTING.html) )

Changelog
--------------

See ./CHANGELOG.rst (or  [CHANGELOG](./CHANGELOG.rst) or
[CHANGELOG](./CHANGELOG.html) )

Documentation
--------------

More extensive documentation can be found in the ./docs directory,
and online at [sbws.rtfd.io](https://sbws.readthedocs.io) and
[this onion service](http://d7pxflytfsmz6uh3x7i2jxzzwea6nbpmtsz5tmfkcin5edapaig5vpyd.onion/)
([v2](http://sdmb3rfvp3wadu6y.onion/)).

## License

This work is in the public domain within the United States.

We waive copyright and related rights in the work worldwide through the
[CC0-1.0 license](https://creativecommons.org/publicdomain/zero/1.0).

You can find a copy of the CC0 Public Domain Dedication along with this
software in ./LICENSE.md

## Authors

See ./AUTHORS.md (or  [AUTHORS](./AUTHORS.MD)