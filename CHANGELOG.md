# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Log line on start up with sbws version, platform info, and library versions
(trac#26751)

### Changed

- Document at which times should v3bw files be generated (#26740)
- Remove test data v3bw file and generate it from the same test. (#26736)
- Make sbws more compatible with system packages: (#26862)
  - Allow a configuration file argument
  - Remove directory argument
  - Create minimal user configuration when running
  - Do not require to run a command to initialize
  - Initialize directories when running
  - Do not require configuration file inside directories specified by the 
    configuration

## [0.6.0] - 2018-07-11

**Important changes**:

- The way users configure logging has changed. No longer are most users
  expected to be familiar with how to configure python's standard logging
library with a config file. Instead we've abstracted out the setting of log
level, format, and destinations to make these settings more accessible to
users. Expert users familiar with [the logging config file format][logconffmt]
can still make tweaks.

Summary of changes:

- Make logging configuration easier for the user.
- Add UML diagrams to documentation. They can be found in docs/source/images/
  and regenerated with `make umlsvg` in docs/.

[logconffmt]: https://docs.python.org/3/library/logging.config.html#logging-config-fileformat

### Added

- UML diagrams to documentation. In docs/ run `make umlsvg` to rebuild them.
  Requires graphviz to be installed.(GHPR#226)
- Add metadata to setup.py, useful for source/binary distributions.
- Add possibility to log to system log. (#26683)

### Fixed

- Measure relays that have both Exit and BadExit as non-exits, which is how
  clients would use them. (GH#217)
- Could not init sbws because of a catch-22 related to logging configuration.
  Overhaul how logging is configured. (GH#186 GHPR#224)
- Call write method of V3BWFile class from the object instance. (#26671)
- Stop calculating median on empty list .(#26666)

### Changed

- Remove is_controller_ok. Instead catch possible controller exceptions and 
log them

### Removed

- Two parsing/plotting scripts in scripts/tools/ that can now be found at
<https://github.com/pastly/v3bw-tools>

## [0.5.0] - 2018-06-26

**Important changes**:

- Result format changed, causing a version bump to 4. Updating sbws to 0.5.0
  will cause it to ignore results with version less than 4.

Summary of changes:

- Keep previously-generated v3bw files
- Allow a relay to limit its weight based on
  RelayBandwidthRate/MaxAdvertisedBandwidth
- 1 CPU usage optimization
- 1 memory usage optimization

### Added

- Use a relay's {,Relay}BandwidthRate/MaxAdvertisedBandwidth as an upper bound
  on the measurements we make for it. (GH#155)
- Ability to only consider results for a given relay valid if they came from
  when that relay is using its most recent known IP address. Thanks Juga.
(GH#154 GHPR#199)
- Maintenance script to help us find functions that are (probably) no longer
  being called.
- Integration test(s) for RelayPrioritizer (GHPR#206)
- Git/GitHub usage guidelines to CONTRIBUTING document (GH#208 GHPR#215)

### Fixed

- Make relay priority calculations take only ~5% of the time they used to (3s
  vs 60s) by using sets instead of lists when selecting non-Authority relays.
(GH#204)
- Make relay list refreshing take much less time by not allowing worker threads
  to dogpile on the CPU. Before they would all start requesting descriptors
from Tor at roughly the same time, causing us to overload our CPU core and make
the process take unnecessarily long. Now we let one thread do the work so it
can peg the CPU on its own and get the refresh done ASAP.
(GH#205)
- Catch a JSON decode exception on malformed results so sbws can continue
  gracefully (GH#210 GHPR#212)

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

[Unreleased]: https://github.com/pastly/simple-bw-scanner/compare/v0.6.0...master
[0.6.0]: https://github.com/pastly/simple-bw-scanner/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/pastly/simple-bw-scanner/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/pastly/simple-bw-scanner/compare/v0.4.0...v0.4.1
