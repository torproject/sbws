Simple Bandwidth Scanner technical details
============================================

:Author: Matt Traudt, juga
:Date: 29 March 2018
:Last Update: 19 Sep 2018
:Status: Draft

.. note:: this document may become an specification of the ``sbws`` method to
   measure relays and/or scale the measuremensts

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
run bandwidth scanners to measure the bandwidth of relays and include their
measurements in their network status votes. Clients use the consensus of these
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
Rome 2018 Tor Project meeting. It aims to be a quick to implement,
easy to maintain replacement for torflow. It should not receive many fancy
features; instead, developer time should be spent on finding and implementing a
better load balancing solution than bandwidth scanning, such as peerflow_.

This document describes the implementation contained within the accompanying
``sbws`` package.

Anatomy of a Tor network using sbws
-----------------------------------

First and foremost, there needs to be one or more webservers that exist
somewhere on the Internet. They MUST serve up a file of at least some minimum
size, and MUST support both HTTP GET and HEAD requests on that file. For both
HTTP verbs, they MUST support requests with the Range header and MUST support
*not* compressing responses. Beyond these requirements, the webservers MAY support
TLS connections, optionally with a valid certificate. Both apache and nginx fit
these requirements.

Every directory authority that wishes to also vote on relay bandwidth (AKA
a bandwidth authority) MUST run one or more sbws scanner clients (or trust
someone to run one or more sbws scanner clients for them). The scanners run
continuously, constantly building two-hop circuits to the previously described
webservers and measuring the amount of bandwidth relays are capable of
handling on these measurement circuit.  Over these circuits it collects RTT
data (by repeatedly requesting a single byte from the webserver) and available
bandwidth data (by starting small and progressively requesting larger amounts
of data until the request takes long enough to fulfill, and then requesting
that amount many times).

Periodically the operator of an sbws scanner MUST run the sbws generate
command in order to generate a :term:`v3bw file`. This aggregates the previous
few days' worth of measurement results into one RTT and one bandwidth per relay
ever measured within the validity period into a single file for the tor process
the bandwidth authority is running to read.  The bandwidth authority includes
these aggregated results in its votes.

Sbws dependencies
-----------------

Sbws scanners run tor for themselves and do not require a system tor process to
exist. Tor MUST be installed, and it SHOULD be any up-to-date version supported
by the network team.

Sbws uses the python library Stem_ to launch and control tor and the python
library Requests_ to make HTTP(S) requests. Both are generally packaged for
most major Linux distributions, and are always available in PyPI.

Configuring the sbws scanner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At the time of writing, sbws sets the following torrc options for the following
reasons when it launches Tor. You can find them in ``sbws/globals.py`` and
``sbws/util/stem.py``.

- ``SocksPort auto``: To proxy requests over Tor.
- ``CookieAuthentication 1``: The easiest way to authenticate to Tor.
- ``LearnCircuitBuildTimeout 0``: To keep circuit build timeouts static.
- ``CircuitBuildTimeout 10``: To give up on struggling circuits sooner.
- ``UseEntryGuards 0``: To avoid path bias warnings.
- ``DataDirectory ...``: To set Tor's datadirectory to be inside sbws's.
- ``PidFile ...``: To make it easier to tell if Tor is running.
- ``ControlSocket ...``: To control Tor.
- ``Log notice ...``: To know what the heck is going on.

How it all works
----------------

We now describe various core parts of sbws.

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

Simple result storage
~~~~~~~~~~~~~~~~~~~~~

Internally, sbws has a hierarchy of ``Result`` classes for easy managing of
different types of result (success, error-because-of-circuit-error,
error-because-[...] etc.). These results get converted into JSON strings and
stored -- **one per line** -- in text files in a data directory.

The text files are simply named after the date. For example:
``2018-03-20.txt``.

The sbws scanner only appends to these files, and it automatically starts a new
file when the system's clock ticks past midnight UTC.

To avoid any weird timezone-related issues, consumers of sbws scanner data (such
as the generate and stats scripts) SHOULD read more files than strictly
necessary. For example, if the validity period is 5 days, they should read 6
days of files. Because all results have a Unix timestamp, consumers of sbws
data can easily determine which results are just outside the validity period as
they are reading them in.


Simple result processing
~~~~~~~~~~~~~~~~~~~~~~~~

Every hour the directory authorities vote to come to a consensus about the
state of the Tor network.  The bandwidth authorities need to use the results
that have been gathered to inform their vote about relays' bandwidths. To do
this they use sbws generate.

This command gathers all recent valid results and organizes them by relay. For
each relay, it first simply calculates the median bandwidth and median RTT of
all its successful results. This is the final RTT value for the relay (it's
only used for informational purposes anyway), but we aren't necessarily done
with the bandwidth values.

To support running in parallel with the legacy torflow_, **XXX Explain scaling***

.. _torflow: https://gitweb.torproject.org/torflow.git
.. _stem: https://stem.torproject.org
.. _requests: https://docs.python-requests.org/
