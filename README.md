# simple-bw-scanner

It doesn't get simplier than this, folks.

Run server.py on the same machine as a relay with an exit policy that allows
exiting to itself on a single port. (Notice: it won't get the exit flag)

Run scanner.py on a well-connected machine on the Internet.

The scanner builds two hop circuits consisting of the relay being measured and
the helper relay running server.py. Over these circuits it measures RTT and
download performance.

# Installing

Clone the repo

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install .
    sbws client -h
    sbws server -h

# Authenticating to server.py

Generate a password and store in passwords.txt. It must be 64 characters (or
bytes?) long and valid unicode. Just use regular ASCII 1-byte chars, as in this
example please. Multiple passwords may be specified, one per line.

    (</dev/urandom tr -dc 'a-zA-Z0-9' | head -c 64; echo '') | tee -a passwords.txt

The scanner will pick the first password and use it always. The server will
accept any password in the file.

----------

Some quick notes to get you started

scanner.py is the client; server.py is the server. The server needs to run next
to an "exit" relay (only needs to allow exiting to one IP+port on its own
machine). 

**scanner.py** is the client that ties everything together. It creates a
circuit builder, relay list, and result dump. It creates a pool of worker
threads to perform measurements. It currently performs one measurement per
relay (in random order) and then quits. Obviously that (and a lot else) needs
to change.

**scanner.py: measure_relay** is the function that runs in a worker thread to
do a measurement. After building a two-hop circuit through the target relay and
the helper "exit" relay and attaching a stream to that circuit, it tells the
server to send 16 KiB. It times how long that takes. If it takes less than a
second, it tells the server to send 10x as much and repeats. If it took longer
than a second, it tells the server to send the amount that we predict would
take just over 5s to send. Once we have a measurement that took longer than 5s,
it sends the resulting speed (and other metadata) to the result dump.

The scanner still needs some work. For example, maybe we should only take a
result that takes between 5s and 10s to retrieve instead of just greater than
5s. Maybe we need to take a small number of similarly sized measurements and
only use the maximum as the result.

**generate-v3bw.py** takes the results from the last 5 days of measurements and
generates a file ready for the bandwidth authorities to consume. It uses the
median measuremnt from the last 5 days, *which is a temporary thing until we
think about what we actually want to do (max? EWMA?)*. It scales the results so
that it can have comparible results to other systems (assuming they use the
same scale).

**lib/circuitbuilder.py** Only one subclass of CircuitBuilder is used as of
this writing, and that is GapsCircuitBuilder. Oddly enough, there are no gaps
in the circuits we ask it to build.
