Switching from helpers to HTTP(S)
=================================

:Author: Matt Traudt
:Date: 25 April 2018
:Last Update: 25 April 2018
:Status: Draft

Some Problems with the sbws helper concept
------------------------------------------

- Twice as many things to keep up to date
- Finding helper operators
- Trusting helper operators
- Home-grown protocol ("but it's totally secure enough for our needs guys,
  trust me. And it's totally implemented correctly too.")

Ways HTTP(S) is less terrible
-----------------------------

- Standard protocols with established security properties
- Easier to "set and forget"
- More flexible in deployment set ups
   - TLS could be optional, but if present, could allow the web server to be
     far away from any Tor relay
   - CDNs could be used ... maybe (no promises)
   - Measurements could still be done 1 relay at a time if there's a way to
     specify that the web server should be considered right next to a specific
     relay(s)

Challenges
----------

Measuring 2 relays at a time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the current design, it's easy to see and believe that sbws only measures one
relay at a time.

In an sbws deployment that uses HTTP(S) servers far away from any Tor relay,
it's harder or impossible. So we need to measure more than one relay at once.
That means we need to come up with a way to select a pair of relays (where one
is an exit, most likely) such that one won't significantly impact the results
for the other.

**Idea 1**:

1. Pick a first hop relay.
2. Collect all exits that have a consensus weight equal or higher to the first
   hop relay. If there are none, collect the single fastest or select the
   ``X`` fastest.
3. Pick one of the collected exits in a weighted random fashion based on their
   consensus weights


**Idea 2**:

Same as the first, but consider all exits not just the ones faster than the
first hop relay.

Supporting many variations on HTTP(S)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By this I mean I would love to support all of the following.

- sbws scanner option for using an HTTPS CDN across all exits in the network
- sbws scanner option for using a specific HTTPS webserver across all exits in
  the network (might not be any different than the previous item)
- sbws scanner option for using a specific HTTP(S) webserver across a specific list
  of relays (which may or may not have the Exit flag)
- in the cases where TLS is used, optional (enabled by default) verification
  the certificate is valid or at least pinned
- in the cases where TLS is used, the optional use of client certificates for
  identification


Proposals
---------

Replace the concepts of "helpers" and "helper relays" and "sbws servers" with
"SOMETHING". "Measurement methods"? "Avenues"? "Destinations"? I'll call them
destinations for now.

Configuration
~~~~~~~~~~~~~

Replace ``[helpers]`` with ``[destinations]``. If you don't remember what this
section is for, it's for enabling/disabling various helpers (or, now
destinations) without removing their config details.

::

    [destinations]
    cloudflare_cdn = on
    pastly_relay = on
    foobar = off

Replace ``[helpers.foo]`` with ``[destinations.foo]``. If you don't remember
what these are for, they are sections for each enabled destination that specify
more specific configuration options for them. In the helper relay world, they
had the relay fingerprint, sbws server host and port, and the password to give
the sbws server.

If there is a combination of options that doesn't make sense, then sbws should
fail to start.

If no destinations are configured, sbws should fail to start.

Sbws should run reachability tests on each destination on startup and then
periodically and make sure they are usable as configured. It should only use
destinations that are usable. If none are usable, it should sleep for a while
and test for usability again later.

Available keys in a ``[destinations.foo]`` section:

- ``relays``: a comma-separated list of relay fingerprints that can be used
  when using this destination. If unspecified, use all relays with the Exit
  flag. If specified, at least one relay must be usable. If it isn't, the
  destination should be considered unusable. (optional)
- ``relay_section_method``: one of ``uniform_random`` or
  ``bw_weighted_random``, defaulting to whichever is a sane default (optional)
- ``url``: an HTTP or HTTPS URL for the bandwidth file to download. The URL's
  hostname must not be resolved locally; instead, it should be left up to the
  exit relay to resolve. If the URL does not contain a path, it defaults to
  ``/sbws.bin``. (required)
- ``weight``: when choosing between which destination to use for the next
  measurement, give this destination the specified weight. If not given,
  defaults to 100. Note how if no destinations have a weight value, they are
  chosen uniformly at random. (optional)

If protocol is https, these additional keys are available in a
``[destionations.foo]``. It is a fatal configuration error to specify any of
these if protocol is http.

- ``client_cert``: path to certificate to provide to the server. If none
  provided, server is only usable if it doesn't require client authentication.
  If provided and file doesn't exist, it is a fatal configuration error. If
  provided and the server doesn't accept it, the destination is unusable.
  (optional)
- ``verify_server_cert``: either a boolean or a path to a file. If yes (the
  default), the server's certificate must be trusted (as determined by the
  local machine's configuration outside of sbws). If no, do no verification of
  the certificate at all. If a path to a file and the file does not exist, it
  is a fatal configuration error. Otherwise, the certificate the server users
  must be present in the file pointed to by this option. (optional)

Example: CDN
'''''''''''''

Relays are not specified because we want to choose from all exits in the
network.

This CDN provides ``/sbws.bin`` so we are allowed to leave off the file part.

HTTPS for the protocol, and no further HTTPS options because this CDN has a
widely-trusted certificate and doesn't care about only allowing our sbws
scanners to download files.

::

    [destinations.cloudflare]
    url = https://sbwsrocks.cdn.cloudflare.com/


Example: Private Local Destination
''''''''''''''''''''''''''''''''''

Here, an authority has decided he doesn't want to trust anyone but themself.
They are running 2 relays on the same machine as a webserver that only they
will use.

This authority chooses to use a client TLS certificate to identify their
scanner(s), so their webserver must use HTTPS.

On their webserver they generate a self-signed certificate.
On the sbws scanner side, they *could* choose to assume everything will be okay
and his server will not change certificates. But they're paranoid, so they get
a copy of the server's certificate and store it in a local file.

.. todo:: What file format?

::

    [destionations.secure_bwauth]
    relays = AAAA...AAAA, BBBB...BBBB
    relay_section_method = uniform_random
    url = https://33.33.33.33:4433/sbws.bin
    client_cert = ${paths:sbws_home}/secure_bwauth_scanner.cert
    verify_server_cert = ${paths:sbws_home}/secure_bwauth_server.cert

Example: "Borrow" bandwidth from unsuspecting mirrors
''''''''''''''''''''''''''''''''''''''''''''''''''''''

This could be considered unethical and therefore a terrible non-starter idea.

It's also a cool thing that I think is technically possible.

Pick a Linux distro that provides ISOs or packages over an HTTP(S) server.
Ideally many servers under a single DNS name that rotates. (Maybe even one that
is geo-aware to give you a close mirror to where you're resolving the name.)

Then just find a file big enough to service all of our possible request sizes,
and add it to the config.

::

    [destination.unsuspecting_linux]
    url = http://examplelinux.net/archive/isos/1.2.3/examplelinux-amd64-gnome-destkop.iso
