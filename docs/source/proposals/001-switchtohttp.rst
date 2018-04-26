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
- ``server_host``: an IPv4 address, IPv6 address, or hostname. If a hostname is
  given, it must not be resolved once at startup; instead, it should be
  left up to the exit relay to resolve. (required)
- ``server_port``: a port (optional, with sane default depending on protocol)
- ``protocol``: one of ``http`` or ``https`` (required)
- ``file_path``: path to the resource to download from the webserver. If not
  specified, defaults to something. It is a fatal configuration error to leave off
  the leading ``/``. (optional)
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
- ``server_cert_fingerprint``: a TLS certificate fingerprint that the server
  must use.  It is a fatal configuration error to specify this but not enable
  ``verify_server_cert``. If not given, the server must use a trusted
  certificate. (optional)
- ``verify_server_cert``: whether to verify the server certificate or not.
  Default yes. If enabled and ``server_cert_fingerprint`` is not given, it must
  be trusted (as determined by the local machine's configuration outside of
  sbws). If enabled and ``server_cert_fingerprint`` is given, the certificate
  from the server must have the specified fingerprint. If enabled but neither
  of those things are true, the server is unusable. (optional)

Example: CDN
'''''''''''''

Relays are not specified because we want to choose from all exits in the
network.

HTTPS for the protocol, and no further HTTPS options because this CDN has a
widely-trusted certificate and doesn't care about only allowing our sbws
scanners to download files.

::

    [destinations.cloudflare]
    server_host = sbwsrocks.cdn.cloudflare.com
    protocol = https

Example: Private Local Destination
'''''''''''''''''''''''''''''''''''

Here, an authority has decided he doesn't want to trust anyone but themself.
They are running 2 relays on the same machine as a webserver that only they
will use.

HTTPS is not technically required to protect credentials flowing over the
Internet. In fact, the webserver isn't even reachable from the Internet!

However, the authority wants to make sure only their sbws scanner(s) can
connect to this webserver, so they technically set up HTTPS. On their webserver
they generate a self-signed certificate. On the sbws scanner side, they *could*
choose to specify the fingerprint of this TLS certificate with
``server_cert_fingerprint``, but instead trust themself to keep their
infrastructure secure and forego verification of the server certificate
entirely.

::

    [destionations.secure_bwauth]
    relays = AAAA...AAAA, BBBB...BBBB
    relay_section_method = uniform_random
    server_host = 33.33.33.33
    server_port = 4433
    protocol = https
    client_cert = ${paths:sbws_home}/secure_bwauth_client.cert
    verify_server_cert = off

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
    server_host = mirror-rotation.exaplelinux.net
    protocol = http
    file_path = /archive/isos/1.2.3/examplelinux-amd64-gnome-destkop.iso
