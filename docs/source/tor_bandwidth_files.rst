How bandwidth files are shown in the Tor network
=================================================

Directory authorities' votes
-----------------------------

moria, using Tor 0.3.5.7:

.. code:: text

    bandwidth-file-headers timestamp=1548181637

https://collector.torproject.org/recent/relay-descriptors/votes/

To appear in Tor v0.4.1.x:

.. code:: text

    bandwidth-file-digest sha256=01234567890123456789abcdefghijkl

https://trac.torproject.org/projects/tor/ticket/26698

Directory authorities' bandwidth file URL
-----------------------------------------

To appear in Tor v0.4.1.x:

.. code:: text

    /tor/status-vote/next/bandwidth.z

https://trac.torproject.org/projects/tor/ticket/21377
