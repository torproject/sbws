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

Running the scanner
---------------------
Overview
~~~~~~~~~

The :term:`scanner` obtain a list of relays from the Tor network.
It measures the bandwidth of each relay by creating a two hop circuit with the
relay to measure and download data from a :term:`destination` Web Server.
The :term:`generator` creates a :term:`bandwidth list file` that is read
by a :term:`directory authority` and used to report relays' bandwidth in its
vote.

.. image:: ./images/scanner.svg
   :height: 200px
   :align: center

Intialization
~~~~~~~~~~~~~~

.. At some point it should be able to get environment variables

#. Parse the command line arguments and configuration files.
#. Launch a Tor thread with an specific configuration or connect to a running
   Tor daemon that is running with a suitable configuration.
#. Obtain the list of relays in the Tor network from the Tor consensus and
   descriptor documents.
#. Read and parse the old bandwidth measurements stored in the file system.
#. Select a subset of the relays to be measured next, ordered by:

   #. relays not measured.
   #. measurements age.

.. image:: ./images/use_cases_data_sources.svg
   :alt: data sources
   :height: 200px
   :align: center

Classes used in the initialization:

.. image:: ./images/use_cases_classes.svg
   :alt: classes initializing data
   :height: 300px
   :align: center

Source code: :func:`sbws.core.scanner.run_speedtest`

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

The relays' bandwidth measurements (``Results``) to be added to the Bandwidth
File MUST be first selected and MUST be then then scaled.

Selecting bandwidth measurements
:::::::::::::::::::::::::::::::::::

Each relay bandwidth measurements are selected in the following way:

1. At least two bandwidth measurements (``Result`` s) MUST have been obtained
   within an arbitrary number of seconds (currently one day).
   If they are not, the relay MUST NOT be included in the Bandwith File.
2. The measurements than are are older than an arbitrary number of senconds
   in the past MUST be discarded.
   Currently this number is the same as ``data_period`` (5 days).

If the number of relays to include in the Bandwidth File are less than
a percententage (currently 60%) than the number of relays in the consensus,
additional Header Lines MUST be added (see XXX) to the Bandwith File and the
relays SHOULD NOT be included.

Scaling bandwidth measurements
:::::::::::::::::::::::::::::::::

Consensus bandwidth obtained by new implementations MUST be comparable to the
consensus bandwidth, therefore they MUST implement torflow_scaling_.
The bandwidth_file_spec_ appendix B describes torflow scaling and a linear
scaling method.

.. _torflow: https://gitweb.torproject.org/torflow.git
.. _stem: https://stem.torproject.org
.. https://github.com/requests/requests/issues/4885
.. _requests: http://docs.python-requests.org/
.. _peerflow: https://www.nrl.navy.mil/itd/chacs/sites/www.nrl.navy.mil.itd.chacs/files/pdfs/16-1231-4353.pdf
.. _torflow_scaling: https://gitweb.torproject.org/torflow.git/tree/NetworkScanners/BwAuthority/README.spec.txt#n298
.. _bandwidth_file_spec: https://gitweb.torproject.org/torspec.git/tree/bandwidth-file-spec.txt