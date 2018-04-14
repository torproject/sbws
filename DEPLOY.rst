Deploying Simple Bandwidth Scanner
----------------------------------

.. todo::

    Determine if the helper exit can specify 127.0.0.1 as the location of
    the sbws server. Replace all instances of **XX1** with the answer.

.. todo::

    Determine if the sbws client and server can be on the same machine.
    Replace all instances of **XX2** with the answer.

.. todo:: mark the terms here as terms for :doc:`glossary`?

.. note:: maybe add here terms from :doc:`glossary`?


So you want to run sbws for yourself. You will need

- A machine to measure from, hereafter referred to as *ClientMachine*.
- One or more machines to measure to, hereafter referred to as *ServerMachine*.

Both ServerMachine and ClientMachine should be on fast, well connected machines.
**XX2** The *ServerMachine* should be on a
machine that is also running a Tor relay, and that Tor relay should be okay
with modifying its exit policy to allow exiting to one local IP on one port
(note that the relay will *not* get the Exit flag). Together, the sbws server
and the Tor relay it is running next to (ideally on the same machine) are
referred to as a *helper*.

First install sbws as in :doc:`/INSTALL`. Make sure you can run ``sbws client
-h`` and ``sbws server -h`` without error before moving on.

**On ClientMachine** ...

For each helper you intend to use, generate a 64 character password. Set these
aside for now in a temporary file. Be ready to copy/paste them. Here we
generate two passwords and store them in a temporary file, annotating which
helper they are for.

::

    $ export pwfile=/tmp/sbws-passwords.txt
    $ echo "#Helper Mine" > $pwfile
    $ sbws pwgen | tee -a $pwfile
    $ echo "#Helper John" >> $pwfile
    $ sbws pwgen | tee -a $pwfile

Now that you have those, open your sbws config file. By default it is located
in ``~/.sbws/config.ini``. If it does not exist, something went wrong, most
likely while calling ``sbws init``.

In the ``[client]`` section, give your client a better nickname.

Create a ``[helpers]`` section. For every helper you intend to use, add a line to
the section. For example, if I plan on using a helper I'm running and one that
John is running, I would add the following:

::

    [helpers]
    mine = on
    john = on

.. note ::

    You can disable helpers without removing them from the config by switching
    "on" to "off"

For every enabled helper, you now need a section for them. In it we give the
details for the helper relay and its sbws server. This is where you'll need
those passwords you generated earlier.

::

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

.. note ::

    ``server_host`` can be an IP address. IPv4 will work. IPv6 will work
    without ``[brackets]``

**XX1**

At this point you are done on ClientMachine for now. You should verify that the
configuration is most likely valid by running a simple sbws command and seeing
if it complains. The following indicates there is no problem.

::

    $ sbws
    usage: sbws [-h] [-v] [-q] [-d DIRECTORY]
                {client,generate,init,pwgen,server,stats} ...
    [ ... more help output ... ]

While the following indicates there is an issue in your config.

::

    $ sbws
    [2018-04-06 08:38:29.122616] [error] [MainThread] client/nickname (Bad_NickName): Letter _ at position 3 is not in allowed characters "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    [2018-04-06 08:38:29.122678] [error] [MainThread] helpers.mine is an enabled helper but is not a section in the config

**On ServerMachine** ...

Recall that ServerMachine is the machine running a Tor relay and the one were we
are about to set up an sbws server.

Minor modifications need to be made to the relay's torrc. Assuming this is a
non-exit relay and you do not want that to change, we need to allow exiting to
a single IP and port, and that IP is on the local machine. This requires a few
torrc options.

::

    # Modifications needed for a non-exit sbws helper relay
    ExitRelay 1
    ExitPolicyRejectPrivate 0
    ExitPolicy accept 33.33.33.33:31648
    ExitPolicy reject *:*
    # End modifications needed for a non-exit sbws helper relay

Replace ``33.33.33.33`` with the IP address of this machine.
**XX1**

If this is an exit relay, you will still need to set
``ExitPolicyRejectPrivate 0`` and allow exiting to a local IP address on a single
port; however, *you should take care to block exiting to the rest of local
address space*. By default Tor would do that for you, but you must now do it
manually. The exit part of your torrc should look something like this.

::

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

Again, replacing ``33.33.33.33`` with the IP address of this machine.
**XX1**

Once you are done editing your torrc, reload Tor. Make sure Tor is still
running.

It's finally time to get to configuring sbws. Open its config file, located at
``~/.sbws/config.ini`` by default. *If this directory or file does not exist,
you probably haven't initialized sbws or something went wrong when you did. The
file should not be empty.*

Add a ``[server]`` section to the config and tell sbws to bind to the IP address
for this machine.

::

    [server]
    bind_ip = 33.33.33.33

**XX1**

Now it's time to tell the sbws which clients we want to allow to use our
server. Gather the 64 character passwords from all the clients you want to
allow and add them to a new ``[server.passwords]`` section.

::

    [server.passwords]
    alice = joyrsUxkpvrlt6ZNxXyP4stdMGohZ5OwyqawvMhevzKq2gDFYjWUSsxMQeG5iIRY
    bob = Ll22MSLm1DOGYXw74c2vyCbnLtRidgaAb7pAOLua62pYoAx8PsTsaC3BN7QUdD4N
    mine = G5YqRhj6J28UFIZzg2TI9ENL6kWZCt7qMsFnpLDVAQMZsgUnrbZIoJtkd4WpjzEf

.. note::

    If you would like to disallow a client from using your server without
    removing their password completely, comment out their line in this section
    and restart the sbws server

To check if the config is valid, run ``sbws`` and check that you get normal usage
output as described earlier while setting up the sbws client.

Once the config is valid, you should be ready to to run ``sbws server`` in
screen, tmux, or something like that.

**On the ClientMachine** ...

Once all the sbws servers that you want to use are running, you can run
``sbws client`` in screen, tmux, or something like that.
