# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Use a relay's {,Relay}BandwidthRate/MaxAdvertisedBandwidth as an upper bound
  on the measurements we make for it. (GH#155)
- Ability to only consider results for a given relay valid if they came from
  when that relay is using its most recent known IP address. Thanks Juga.
(GH#154 GHPR#199)
- Maintenance script to help us find functions that are (probably) no longer
  being called.
- Integration test(s) for RelayPrioritizer (GHPR#206)

### Fixed

- Make relay priority calculations take only ~5% of the time they used to (3s
  vs 60s) by using sets instead of lists when selecting non-Authority relays.
(GH#204)

### Changed

- Change the path where the Bandwidth List files are generated: now they are
  stored in `v3bw` directory, named `YYmmdd_HHMMSS.v3bw`, and previously
generated ones are kept. A `latest.v3bw` symlink is updated. (GH#179 GHPR#190)
- Code refactoring in the v3bw classes and generation area
- Replace v3bw-into-xy bash script with python script to handle a more complex
  v3bw file format (GH#182)

## [0.4.1] - 2018-06-14

### Changed

- If the relay to measure is an exit, put it in the exit position and choose a
  non-exit to help. Previously the relay to measure would always be the first
hop. (GH#181)
- Try harder to find a relay to help measure the target relay with two changes.
  Essentially: (1) Instead of only picking from relays that are 1.25 - 2.00
times faster than it by consensus weight, try (in order) to find a relay that
is at least 2.00, 1.75, 1.50, 1.25, or 1.00 times as fast. If that fails,
instead of giving up, (2) pick the fastest relay in the network instead of
giving up. This compliments the previous change about measuring target exits in
the exit position.

### Fixed

- Exception that causes sbws to fall back to one measurement thread. We first
  tried fixing something in this area with `88fae60bc` but neglected to
remember that `.join()` wants only string arguments and can't handle a `None`.
So fix that.
- Exception when failing to get a relay's `ed25519_master_key` from Tor and
  trying to do `.rstrip()` on a None.
- `earliest_bandwidth` being the newest bw not the oldest (thanks juga0)
- `node_id` was missing the character "$" at the beginning

[Unreleased]: https://github.com/pastly/simple-bw-scanner/compare/v0.4.1...master
[0.4.1]: https://github.com/pastly/simple-bw-scanner/compare/v0.4.0...v0.4.1
