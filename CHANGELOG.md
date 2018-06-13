# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Exception that causes sbws to fall back to one measurement thread. We first
  tried fixing something in this area with `88fae60bc` but neglected to
remember that `.join()` wants only string arguments and can't handle a `None`.
So fix that.


[Unreleased]: https://github.com/pastly/simple-bw-scanner/compare/v0.4.0...master
