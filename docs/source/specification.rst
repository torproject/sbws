Simple Bandwidth Scanner Specification
======================================

:Author: Matt Traudt
:Date: 29 March 2018
:Status: Draft

Conventions
-----------

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL"
in this document are to be interpreted as described in BCP 14 (:rfc:`2119`
and :rfc:`8174`) when, and only when, they appear in all capitals, as shown
here.

Background
----------

Some of the Tor :term:`directory authorities <directory authority>`
runs bandwidth scanners to measure the bandwidth of relays and include their
measurements in their network status votes.  Scanner use the consensus of these
weights to inform their path selection process with the hope that every circuit
they build will have roughly equal performance, regardless of the relays
chosen. This achieves a form of load balancing.

.. _problem:

Historically, the directory authorities that ran bandwidth scanners
(:term:`bandwidth authorities <bandwidth authority>`), ran torflow_. Time
passed, it slowly become less maintained, and the collective knowledge of how
it worked slipped away.

The bandwidth authorities became increasingly unhappy having to run torflow.
Twice yearly Tor Project meetings came and went. Everyone agreed a replacement
was needed, but it was harder to reach consensus on what it should look like
and what its goals where.

Simple Bandwidth Scanner (sbws) is a project motivated by discussions at the
Rome 2018 Tor Project meeting. This document describes the implementation
contained within the accompanying ``sbws`` package.

First we cover the parts of sbws that continuously perform measurements;
namely, the scanner that builds 2 hop Tor circuits through a target and helper
relay to a waiting server. Next we describe the process of periodically turning
recently gathered results into an aggregate format ready for including in a
bandwidth authority's votes.

Anatomy of a Tor network using sbws
-----------------------------------

First and foremost, the Tor network needs one or more helper relays to act as
exits in the two hop circuits that sbws measurement scanners build. These helper
relays need not be proper exits, but merely must support exiting to a single IP
address and port, at which is listening an sbws server. Ideally the helper
relay and sbws server are running on the same physical hardware. The sbws
servers listen for scanners to authenticate to them, and once successfully
authenticated, wait for scanners to request arbitrary numbers of bytes to be
sent to them.

Every directory authority that wishes to also vote on relay bandwidth must then
run one or more sbws scanners. The scanners run continuously, constantly building
circuits and measuring the amount of bandwidth each relay is capable of
handling on the measurement circuit. Over these circuits it collects RTT data
(by repeatedly requesting a single byte from the server) and available
bandwidth data (by starting small and progressively requesting larger amounts
of data until the request takes long enough to fulfill, and then requesting
that amount many times).

When a bandwidth authority is ready to vote, it runs the sbws generate process.
This aggregates the previous few days' worth of measurement results into one
RTT and one bandwidth per relay ever measured within the validity period. The
bandwidth authority includes these aggregated results in its votes.

Configuring Tor and sbws
------------------------

.. note:: i'd move all section 2 to :doc:`DEPLOY` and :doc:`config`

Sbws does not require any complicated modifications to Tor. For all parts of
sbws that interact with a Tor daemon, only a couple of simple configuration
changes are required.

Sbws uses Stem_ to communicate with Tor over its ControlPort and PySocks_ to proxy
traffic over Tor's SocksPort.

Configuring the sbws server
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For an sbws server, its helper relay must have a few exit options set.

::

    ExitRelay 1
    ExitPolicyRejectPrivate 0
    ExitPolicy accept 555.555.555.555:4444
    ExitPolicy reject *:*

**XXX Check if the IP address can be in 127/8 on better-configured machines.**

First we enable exiting. Then we have to tell Tor it's okay to exit to IP
addresses on the local machine. Finally we have a simple exit policy that
allows exiting to the local machine on a single port and rejects all other exit
traffic. *The relay will not get the exit flag.*

Configuring the sbws scanner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For an sbws scanner, its Tor scanner configuration is even simpler. In addition
to making sure it has a SocksPort, ControlPort, and some form of ControlPort
authentication enabled, it is recommended circuit build timeout options be set
as such.

::

    LearnCircuitBuildTimeout 0
    CircuitBuildTimeout 10

When the sbws scanner starts up and connects to Tor, it will set the following
two options.

::

    __DisablePredictedCircuits 1
    __LeaveStreamsUnattached 1

The former simply to cut down on the number of unused circuits and the latter
so that the scanner can attach streams to circuits manually.

Sbws scanner/server authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**XXX This will be changed very soon to be more user friendly, but the idea is
the same.**

The sbws scanner keeps a ``passwords.txt`` file containing a single non-comment
line containing a 64 character password consisting only of characters in the
space ``a-zA-Z0-9``.

The sbws similarly keeps a ``passwords.txt``, but its contains many 64
character passwords. When a scanner connects, it must provide one of the 64
character passwords in the server's ``passwords.txt``.

How it all works
----------------

We now describe various core parts of sbws.

Selecting the relays to measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. todo:: explain here how relays are selected (random),
apart of the prioritization below

Simple relay prioritization
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This may be the most complex part of sbws.

Sbws makes an effort to prioritize measurements of relays that don't have many
recent results. For example: relays that just joined the Tor network or relays
that haven't been online in the past few days. This goal is achieved using a
min-priority queue and the concept of *freshness*.

Freshness is defined as the amount of time between when the measurement was
made and the time sbws will stop considering it valid. Thus, a measurement made
more recently will have more time until it is no longer valid (higher
freshness) and a measurement made a long time ago will have very little time
until it is no longer valid (lower freshness).

Over time, sbws will make many measurements for a given relay. The sum of these
measurements' freshnesses is the relay's priority. As we are prioritizing like
a min-priority queue, a higher sum of freshnesses means *worse* priority while
a lower sum of freshnesses means *better* priority.

  Example: AlphaRelay33 joined the network yesterday and sbws has measured it
  once so far. BetaRelay87 has been in the network for years and has been
  getting measured regularly approximately once a day. BetaRelay87 has five
  measurements that are still valid, with freshnesses 10, 100, 500, 1000, and
  1500. AlphaRelay33's one measurement has freshness 3000. Because the sum of
  BetaRelay87's 5 measurements is greater than AlphaRelay33's one measurement,
  AlphaRelay33 has *better* priority and will be measured next before
  BetaRelay87.

  Example: AlphaRelay33 is still a brand new relay with its one measurement
  in the last day with freshness 3000. CharlieRelay9 has been in the network
  for a long time, but had technical issues last week and hasn't been online in
  many days. When CharlieRelay9's operator finally gets him back online, he
  still has one valid measurement with freshness 10. Because AlphaRelay33's
  measurement is fresher, CharlieRelay9 has *better* priority and will get
  measured first.

Sometimes measurements fail. Hopefully they fail because of transient issues,
and with that hope in mind, it would be nice if a relay with a failed
measurement didn't have to wait a long time to have another chance at a
successful measurement. For this reason, when summing the freshnesses of
results for a given relay, sbws will artificially *reduce* the freshness for
measurements that were not successful. This makes the sum of freshnesses lower
for that relay, and therefore the priority *better* so it can be measured again
sooner.

Simple wire protocol
~~~~~~~~~~~~~~~~~~~~

In this subsection, the scanner/server communication that takes place after a
Tor circuit is built and a TCP connection created in it is described.

Simple handshake
''''''''''''''''

After initiating a TCP connection over Tor to the server, the sbws scanner sends
4 magic bytes indicating it intends to speak sbws' protocol. If the first four
bytes an sbws server receives are not the correct magic bytes, the server
SHOULD close the connection.

If the scanner sends the correct magic bytes, the server does nothing in
response. Therefore, the scanner SHOULD immediately followup with the version of
the wire protocol it will speak. This version is an integer, but is sent as a
string followed by a newline. So version 1 would be sent as the two byte
string, ``"1\n"``.

If the server does not support the version that the scanner sent, it MUST
immediately close the connection.  Otherwise, the server does nothing in
response. Therefore, the scanner SHOULD immediately followup with its 64
character password.

Upon receiving the scanner's full password, the server checks if it is valid. If
it is invalid, the server MUST immediately close the connection. Otherwise, the server
MUST send to the scanner the 1 byte success code.

Once the scanner receives the success code, the handshake is complete and the
simple loop may begin.

Simple loop
'''''''''''

To begin the loop, the sbws scanner decides how many bytes it would like to
download from the server. To inform the server, it encodes an integer as text
followed by a newline character. For example, to request 123 bytes, the scanner would
send to the server the string of four bytes ``"123\n"``.

After indicating success to the scanner in the simple handshake, the server
begins listening for the scanner to send a line as described above. Once the
server reads a newline character (``'\n'``), it parses the string into an
integer and proceeds to send the scanner that many bytes as fast as possible.

Immediately after requesting some amount of bytes from the server, the scanner
begins listening for the server to respond with arbitrary bytes until it has
sent the amount it was expecting. At this point the scanner MUST close the
connection if it does not wish to make any more requests. Otherwise, the simple
loop starts over.

Simple Result Storage
~~~~~~~~~~~~~~~~~~~~~

Internally, sbws has a hierarchy of ``Result`` classes for easy managing of
different types of result (success, error-because-of-circuit-error,
error-because-[...] etc.). These results get converted into JSON strings and
stored -- **one per line** -- in text files in a data directory.

The text files are simply named after the date. For example:
``2018-03-20.txt``.

The sbws scanner only appends to these files, and it automatically starts a new
file when the system's clock ticks past midnight.

To avoid any weird timezone-related issues, consumers of sbws scanner data (such
as the generate and stats scripts) should read more files than strictly
necessary. For example, if the validity period is 5 days, they should read 6
days of files. Because all results have a Unix timestamp, consumers of sbws
data can easily determine which results are just outside the validity period as
they are reading them in.

This is a successful result.

::

    {
      "nickname": "test007r",
      "circ": [
        "35ABD93AA6F6EAC9A5690D205961C043F56E8D5B",
        "DB0E268A2BA8A061F03F1F3BA98A0155B4608A23"
      ],
      "type": "success",
      "fingerprint": "35ABD93AA6F6EAC9A5690D205961C043F56E8D5B",
      "rtts": [
        0.01746225357055664,
        0.02101755142211914,
        0.019290447235107422,
        0.019827604293823242,
        0.019453763961791992,
        0.019289731979370117,
        0.02017045021057129,
        0.018725872039794922,
        0.019000768661499023,
        0.019316434860229492
      ],
      "downloads": [
        {
          "amount": 42609660,
          "duration": 6.512440204620361
        },
        {
          "amount": 42609660,
          "duration": 6.519377708435059
        },
        {
          "amount": 42609660,
          "duration": 6.640781879425049
        },
        {
          "amount": 42609660,
          "duration": 6.742352485656738
        },
        {
          "amount": 42609660,
          "duration": 6.292598724365234
        }
      ],
      "version": 1,
      "server_host": "127.0.0.1",
      "scanner": "PastlyDesktop",
      "time": 1522715280.8080218,
      "address": "127.0.0.1"
    }


And this is an example result from a failed measurement.

::

    {
      "circ": [
        "51C56AC6368C7116548CBE3882931CC7223AA657",
        "DB0E268A2BA8A061F03F1F3BA98A0155B4608A23"
      ],
      "address": "127.0.0.1",
      "msg": null,
      "fingerprint": "51C56AC6368C7116548CBE3882931CC7223AA657",
      "scanner": "PastlyDesktop",
      "version": 1,
      "nickname": "test001a",
      "server_host": "127.0.0.1",
      "type": "error-auth",
      "time": 1522715568.0314171
    }


Simple result processing
~~~~~~~~~~~~~~~~~~~~~~~~

.. note:: "Periodically": how much time should that be?

Periodically the bandwidth authorities need to use the results that have been
gathered to inform their vote about relays' bandwidths. To do this they use
sbws generate.

This command gathers all recent valid results and organizes them by relay. For
each relay, it first simply calculates the median bandwidth and median RTT of
all its results. This is the final RTT value for the relay (it's only used for
informational purposes anyway), but we aren't done with the bandwidth values.

To support running in parallel with the legacy torflow_, **XXX Explain scaling***

.. _torflow: https://gitweb.torproject.org/torflow.git
.. _stem: https://stem.torproject.org
.. _pysocks: https://pypi.python.org/pypi/PySocks
