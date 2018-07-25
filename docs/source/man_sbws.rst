Simple Bandwidth Scanner - SBWS(1)
===================================

SYNOPSIS
--------

sbws [**Optional arguments**] [**Positional arguments**]

sbws [**-h**] [**--version**] [**--log-level** {**debug,info,warning,error,critical**}] [**-d** DIRECTORY] {**cleanup,scanner,generate,init,stats**}

DESCRIPTION
-----------

Tor bandwidth scanner that generates bandwidth measurements files to be read by
the Directory Authorities.

OPTIONS
-------

Positional arguments
~~~~~~~~~~~~~~~~~~~~

{**cleanup,scanner,generate,init,stats**}

Optional arguments
~~~~~~~~~~~~~~~~~~

-h, --help
   Show help message and exit.

--version
   sbws version

--log-level {debug,info,warning,error,critical}
   Override the sbws log level (default: None)

-d DIRECTORY, --directory DIRECTORY
   Path to the sbws home directory (default: $HOME/.sbws)

EXAMPLES
--------

sbws -c ~/.sbwsrc scanner
    Run the scanner using the configuration file in ~/.sbwsrc

sbws --log-level debug generate
    Generate v3bw file in the default v3bw directory (~/.sbws/v3bw)

sbws cleanup
    Cleanup datadir and v3bw files older than XX in the default v3bw directory (~/.sbws/)

FILES
-----

$HOME/.sbws.ini
   Default location for the sbws user configuration file.

$HOME/.sbws
   Default sbws home, where it stores measurement data files,
   bandwidth list files and tor process data.

SEE ALSO
---------

**sbws.ini** (5), https://sbws.readthedocs.org.

BUGS
----

Please report bugs at https://trac.torproject.org/.