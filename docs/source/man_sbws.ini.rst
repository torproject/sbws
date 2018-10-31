Simple Bandwidth Scanner - SBWS.INI(5)
======================================

DESCRIPTION
-----------

Tor bandwidth scanner configuration file.

**sbws** (1) ``scanner`` command requires a configuration file with a
"[destinations]" section.

It is the only section that does not have a default value.

It is recommended, but not required to configure "nickname" in the "[scanner]"
section.


SECTIONS
---------

general
  data_period = INT
    Days into the past that measurements are considered valid. (Default: 5)
  http_timeout = INT
    Timeout in seconds to give to the python Requests library. (Default: 10)
  circuit_timeout = INT
    Timeout in seconds to create circuits. (Default: 10)
  reset_bw_ipv4_changes = {on, off}
    Whether or not to reset the bandwidth measurements when the relay's IP
    address changes. If it changes, we only consider results for the relay that
    we obtained while the relay was located at its most recent IP address.
    (Default: on)
  reset_bw_ipv6_changes = off
    NOT implemented for IPv6.

paths

  When **sbws** is run as a system service, `~/.sbws` is changed to
  `/var/lib/sbws`.

  sbws_home = STR
    sbws home directory. (Default: ~/.sbws)
  datadir = STR
    Directory where sbws stores temporal bandwidth results files.
    (Default: ~/.sbws/datadir)
  v3bw_dname = STR
    Directory where sbws stores the bandwidth list files.
    These are the files to be read by the Tor Directory Authorities.
    (Default: ~/.sbws/v3bw)
  v3bw_fname = STR
    File names of the bandwidth list files.
    The latest bandwidth file is symlinked by ``latests.v3bw``
  started_filepath = STR
    File path to store the timestamp when the scanner was last started.
    (Default: ~/.sbws/started_at)
  log_dname = STR
    Directory where to store log files when logging to files is enabled.
    (Default ~/.sbws/log)

destinations
  STR = {on, off}
    Name of destination. It is a name for the Web server from where to
    download files in order to measure bandwidths.

  usability_test_interval = INT
    How often to check if a destination is usable

destinations.STR
  url = STR
    The URL to the destination. It must include a file path.
    It can use both http or https.

tor

  When **sbws** is run as a system service `~/.sbws/tor` is replaced by
  `/run/sbws/tor`.

  datadir = STR
    sbws' owned tor directory. (Default: ~/.sbws/tor)
  control_socket = STR
    sbws's owned tor control socket file.
    (Default: ~/.sbws/tor/sbws/control)
  pid = STR
    sbws's owned tor pid file. (Default: ~/.sbws/tor/sbws/tor.pid)
  log = STR
    sbws's owned tor directory log files. (Default: ~/.sbws/tor/log)
  extra_lines =
    sbws's tor extra configuration. (Default: None)

scanner
  nickname = STR
    A human-readable string with chars in a-zA-Z0-9 to identify the scanner.
    (Default: IDidntEditTheSBWSConfig)
  download_toofast = INT
    Limits on what download times are too fast/slow/etc. (Default: 1)
  download_min = INT
    Limits on what download times are too fast/slow/etc. (Default: 5)
  download_target = INT
    Limits on what download times are too fast/slow/etc. (Default: 6)
  download_max = INT
    Limits on what download times are too fast/slow/etc. (Default: 10)
  num_rtts = INT
    How many RTT measurements to make. (Default: 10)
  num_downloads = INT
    Number of downloads with acceptable times we must have for a relay before
    moving on. (Default: 5)
  initial_read_request = INT
    The number of bytes to initially request from the server. (Default: 16384)
  measurement_threads = INT
    How many measurements to make in parallel. (Default: 3)
  min_download_size = INT
    Minimum number of bytes we should ever try to download in a measurement.
    (Default: 1)
  max_download_size = INT
    Maximum number of bytes we should ever try to download in a measurement.
    (Default: 1073741824) 1073741824 == 1 GiB

relayprioritizer
  measure_authorities = {on, off}
    Whether or not to measure authorities. (Default: off)
  fraction_relays = FLOAT
    The target fraction of best priority relays we would like to return.
    0.05 is 5%. In a 7000 relay network, 5% is 350 relays. (Default: 0.05)
  min_relays = INT
    The minimum number of best priority relays we are willing to return.
    (Default: 50)

cleanup
  stale_days = INT
    After this many days, compress data files. (Default: 10)
  rotten_days = INT
    After this many days, delete data files. (Default: 90)

logging
  to_file = {yes, no}
    Whether or not to log to a rotating file the directory paths.log_dname.
    (Default: no)
  to_stdout = {yes, no}
    Whether or not to log to stdout. (Default: yes)
  to_syslog = {yes, no}
    Whether or not to log to syslog. (Default: no)
  to_file_max_bytes = INT
    If logging to file, how large (in bytes) should the file be allowed to get
    before rotating to a new one. 10485760 is 10 MiB. If zero or number of
    backups is zero, never rotate the log file. (Default: 10485760)
  to_file_num_backups = INT
    If logging to file, how many backups to keep. If zero or max bytes is zero,
    never rotate the log file. (Default: 50)
  level = {debug, info, warning, error, critical}
    Level to log at. (Default: info)
  to_file_level = {debug, info, warning, error, critical}
    Level to log at when using files. (Default: info)
  to_stdout_level = {debug, info, warning, error, critical}
    Level to log at when using stdout. (Default: info)
  to_syslog_level = {debug, info, warning, error, critical}
    Level to log at when using syslog. (Default: info)
  format = STR
    Format string to use when logging.
    (Default: [%(asctime)s] [%(name)s] [%(levelname)s] %(message)s)
  to_file_format = STR
    Format string to use when logging to files. (Default: $format)
  to_stdout_format = STR
    Format string to use when logging to stdout. (Default: $format)
  to_syslog_format = STR
    Format string to use when logging to syslog.
    (Default: %(module)s[%(process)s]: <%(levelname)s> %(message)s)

EXAMPLES
--------

Example ``destinations`` section::

    [destinations]
    foo = on
    bar = on
    baz = off

    [destinations.foo]
    # using HTTP
    url = http://example.org/sbws.bin

    [destinations.bar]
    # using HTTPS
    url = https://example.com/data

    [destinations.baz]
    # this will be ignored
    url = https://example.net/ask/stan/where/the/file/is.exe

FILES
-----

$HOME/.sbws.ini
   Default ``sbws`` user configuration path.

Any other path to the configuration file can be specified using the
``sbws`` argument ``-c``

SEE ALSO
---------

**sbws** (1), https://sbws.readthedocs.org.

BUGS
----

Please report bugs at https://trac.torproject.org/.