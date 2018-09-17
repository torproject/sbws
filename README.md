# Readme

[![Build Status](https://travis-ci.org/torproject/sbws.svg?branch=master)](https://travis-ci.org/https://travis-ci.org/torproject/sbws)

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

## License

This work is in the public domain within the United States.

We waive copyright and related rights in the work worldwide through the
[CC0-1.0 license](https://creativecommons.org/publicdomain/zero/1.0).

You can find a copy of the CC0 Public Domain Dedication along with this
software in ./LICENSE.md

## Authors

See ./AUTHORS.md