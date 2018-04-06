# Readme

It doesn't get simpler than this, folks.

Run `sbws server` on the same machine as a relay with an exit policy that
allows exiting to itself on a single port. (Notice: it won't get the exit flag)

Run `sbws client` on a well-connected machine on the Internet.

The scanner builds two hop circuits consisting of the relay being measured and
the helper relay running server.py. Over these circuits it measures RTT and
download performance.

## Boring things

### Versioning

This project follows [semantic versioning][] and thus every major version has
the potential for breaking changes. You can find information about what those
are at the following places.

- In [`CHANGELOG.md`](/CHANGELOG.md)

[semantic versioning]: https://semver.org/

In addition to the overall semantic version for sbws as a whole, there are
simple integer versions for (i) the protocol sbws clients and servers use to
speak to each other, and (ii) the format in which results are stored.
Incrementing either of these version numbers requires a major version change
for sbws. (Note that the reverse is **not** true: a major sbws version change
does not require the integer versions for the wire protocol or result format to
change)

### The public API for sbws

As required by semantic versioning, the public API for sbws will not change
without a major version bump. The public API is

- **The available configuration options and their defaults**. New options may
  be added without a major version bump, but no options will be removed, nor
will defaults be drastically changed. Examples of drastic changes to defaults
include obvious things like flipping any boolean value or a location for data
storage, but also more subjective things, such as increasing the target
download time significantly (6s to 60s). Examples of an insignificant change
include changing the default client nickname. Rule of thumb: if it is likely to
affect results or sbws behavior significantly, it is a major change.

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

- **The wire protocol**. The way `sbws client` and `sbws server` speak will not
  change in a backward incompatible way without both a major version bump and a
bump in the wire protocol version integer.

- **NOT the name, location, signature, or existance of python functions**. Sbws
  is meant to be ran as a standalone program. It is not at all meant to be
treated or used like a library. Users of sbws do *not* need an understanding of
how its code is laid out. Therefore the code may change drastically without a
major version bump as long as the way users interact with it does not change in
a backward incompatible way.

### License

This project is released to the public domain under the CC0 1.0 Universal
license. See [`LICENSE.md`](/LICENSE.md) for more information.

## Installing

Clone the repo

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install .
    sbws init
    sbws client -h
    sbws server -h

## Authenticating to `sbws server`

**XXX Write this.**

## Documentation

See more documentation in [/docs/source/](/docs/source/)

## Configuration

Sbws has two config files it reads.

It first reads the config file containing the default values for almost all
options. If you installed sbws in a virtual environment located at /tmp/venv, then
you will probably find the `config.default.ini` in a place such as
`/tmp/venv/lib/python3.5/site-packages/sbws/`
**You should never edit this file**. You can also click on
[this link](/sbws/config.default.ini) to see the default config file if you're
reading this on GitHub.

Sbws then reads your custom config file. By default, after running `sbws init`,
it is located in `~/.sbws/config.ini`. A configuration option in this file
overwrites the default file found in the default file.

**No other configuration files are read.** The only files that are read are the
`config.default.ini` file located in a place the user shouldn't touch, and the
`config.ini` in their `.sbws` directory.

## The `.sbws` directory

By default is `~/.sbws`. You can choose a different one by specifying `-d` when
calling sbws.

    sbws -d /tmp/testing-dotsbws init
    sbws -d /tmp/testing-dotsbws client

In this directory you will find

- `config.ini` The configuration file you should be editing if you want to
  modify sbws's behavior.
- `datadir` Once your sbws client has started gathering results, it will dump
  them into this directory. Other sbws commands (such as generate and stats)
  read results from the files in this directory.

## Running sbws for the first time

So you want to run sbws for yourself. You will need

- A machine to measure from, hereafter referred to as *mach-client*.
- One or more machines to measure to, hereafter referred to as *mach-server*.

Both mach-server and mach-client should be on fast, well connected machines.
(**XXX can they be on the same machine?**) The *mach-server* should be on a
machine that is also running a Tor relay, and that Tor relay should be okay
with modifying its exit policy to allow exiting to one local IP on one port
(note that the relay will *not* get the Exit flag). Together, the sbws server
and the Tor relay it is running next to (ideally on the same machine) are
referred to as a *helper*.

First install sbws as described elsewhere. Make sure you can run `sbws client
-h` and `sbws server -h` without error before moving on.

**On mach-client** ...

For each helper you intend to use, generate a 64 character password. Set these
aside for now in a temporary file. Be ready to copy/paste them. Here we
generate two passwords and store them in a temporary file, annotating which
helper they are for.

    $ export pwfile=/tmp/sbws-passwords.txt
    $ echo "#Helper Mine" > $pwfile
    $ sbws pwgen | tee -a $pwfile
    $ echo "#Helper John" >> $pwfile
    $ sbws pwgen | tee -a $pwfile

Now that you have those, open your sbws config file. By default it is located
in `~/.sbws/config.ini`. *If it does not exist, something went wrong, most
likley while calling `sbws init`*.

In the `[client]` section, give your client a better nickname.

Create a `[helpers]` section. For every helper you intend to use, add a line to
the section. For example, if I plan on using a helper I'm running and one that
John is running, I would add the following:

    [helpers]
    mine = on
    john = on

(Note that you can disable helpers without removing them from the config by
switching "on" to "off")

For every enabled helper, you now need a section for them. In it we give the
details for the helper relay and its sbws server. This is where you'll need
those passwords you generated earlier.

    [helpers.mine]
    relay = 6B4ABE3FA1D4D0D4AEF2FD6C535891333591D06E
    server_host = freebird.system33.pw
    server_port = 31648
    password = G5YqRhj6J28UFIZzg2TI9ENL6kWZCt7qMsFnpLDVAQMZsgUnrbZIoJtkd4WpjzEf
    
    [helpers.john]
    relay = 09FA8B4F665AD65D2C2A49870F1AA3BA8811E449
    server_host = stanmarsh.system33.pw
    server_port = 31648
    password = 6me6bTM7I4yDdzJ6cjZR0PUx5APFvpOLovA2NzNvyWigI3y42bQXDnB3JrG5kprq

(Note that `server_host` can be an IP address. IPv4 will work, IPv6 is
untested)

(**XXX Can it be 127.0.0.1 ???**)

At this point you are done on mach-client for now. You should verify that the
configuration is most likely valid by running a simple sbws command and seeing
if it complains. The following indicates there is no problem.

    $ sbws
    usage: sbws [-h] [-v] [-q] [-d DIRECTORY]
                {client,generate,init,pwgen,server,stats} ...
    [ ... more help output ... ]

While the following indicates there is an issue in your config.

    $ sbws
    [2018-04-06 08:38:29.122616] [error] [MainThread] client/nickname (Bad_NickName): Letter _ at position 3 is not in allowed characters "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    [2018-04-06 08:38:29.122678] [error] [MainThread] helpers.mine is an enabled helper but is not a section in the config

**On mach-server** ...

Recall that mach-server is the machine running a Tor relay and the one were we
are about to set up an sbws server.

Minor modifications need to be made to the relay's torrc. Assuming this is a
non-exit relay and you do not want that to change, we need to allow exiting to
a single IP and port, and that IP is on the local machine. This requires a few
torrc options.

    # Modifications needed for a non-exit sbws helper relay
    ExitRelay 1
    ExitPolicyRejectPrivate 0
    ExitPolicy accept 33.33.33.33:31648
    ExitPolicy reject *:*
    # End modifications needed for a non-exit sbws helper relay

Replace `33.33.33.33` with the IP address of this machine. (**XXX can
localhost be used?**)

If this is an exit relay, you will still need to set
`ExitPolicyRejectPrivate 0` and allow exiting to a local IP address on a single
port; however, *you should take care to block exiting to the rest of local
address space*. By default Tor would do that for you, but you must now do it
manually. The exit part of your torrc should look something like this.

    # Exit relay config with modifications needed to run an sbws helper relay
    ExitRelay 1
    ExitPolicyRejectPrivate 0
    ExitPolicy reject 0.0.0.0/8:*
    ExitPolicy reject 169.254.0.0/16:*
    ExitPolicy reject 127.0.0.0/8:*
    ExitPolicy reject 192.168.0.0/16:*
    ExitPolicy reject 10.0.0.0/8:*
    ExitPolicy reject 172.16.0.0/12:*
    [ ... Your usual ExitPolicy options should be here, then ... ]
    ExitPolicy accept 33.33.33.33:31648
    ExitPolicy reject *:*
    # End exit relay config and modifications needed for an exit sbws helper relay

Again, replacing `33.33.33.33` with the IP address of this machine.
(**XXX can localhost be used?**)

Once you are done editing your torrc, reload Tor. Make sure Tor is still
running.

It's finally time to get to configuring sbws. Open its config file, located at
`~/.sbws/config.ini` by default. *If this directory or file does not exist,
you probably haven't initialized sbws or something went wrong when you did. The
file should not be empty.* 

Add a `[server]` section to the config and tell sbws to bind to the IP address
for this machine.

    [server]
    bind_ip = 33.33.33.33

**XXX Again, can this be localhost?**

Now it's time to tell the sbws which clients we want to allow to use our
server. Gather the 64 character passwords from all the clients you want to
allow and add them to a new `[server.passwords]` section.

    [server.passwords]
    alice = joyrsUxkpvrlt6ZNxXyP4stdMGohZ5OwyqawvMhevzKq2gDFYjWUSsxMQeG5iIRY
    bob = Ll22MSLm1DOGYXw74c2vyCbnLtRidgaAb7pAOLua62pYoAx8PsTsaC3BN7QUdD4N
    mine = G5YqRhj6J28UFIZzg2TI9ENL6kWZCt7qMsFnpLDVAQMZsgUnrbZIoJtkd4WpjzEf

(Note if you would like to disallow a client from using your server without
removing their password completely, comment out their line in this section and
restart the sbws server)

To check if the config is valid, run `sbws` and check that you get normal usage
output as described earlier while setting up the sbws client.

Once the config is valid, you should be ready to to run `sbws server` in
screen, tmux, or something like that.

**On the mach-client** ...

Once all the sbws servers that you want to use are running, you can run
`sbws client` in screen, tmux, or something like that.

## Build HTML documentation

    pip install -e .[doc]
    cd docs
    make html

The generated HTML will be in [/docs/build/](/docs/build/)

## Running tests

Make sure you have test dependencies installed. From within the top level
repository directory:

    pip install -e .[test]

This should install tox and pytest.

Since my development environment has Python 3.5 and tox is only configured to
test 3.5, both the `tox` and `pytest` commands have the same result. Once sbws
gets properly open source, Travis should run tox with a variety of Python 3.X
versions.

To run the tests, run `pytest`. To generate HTML output of test coverage, run
`pytest --cov --cov-report=html`. A `htmlcov` directory will be created in
current working directory. Open it in a web browser and prepare to be amazed.
It will highlight (un)covered lines! How cool is that?!
