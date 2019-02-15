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

How it all works
----------------

We now describe various core parts of sbws.

In which order are relays measured?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: sbws.lib.relayprioritizer.RelayPrioritizer.best_priority
   :noindex:

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