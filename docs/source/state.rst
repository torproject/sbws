The ``state.dat`` file
======================

This file contains state that multiple sbws commands may want access to and
that needs to persist across processes. Both read and write access to this file
is wrapped in the ``State`` class, allowing for safe concurrent access: the
file is locked before reading or writing, and (for now) only simple data types
are allowed so we can be sure to update the state file on disk every time the
state is modified in memory.

At the time of writing, the following fields can exist in the state file.

``scanner_started``
-------------------

The last time ``sbws scanner`` was started.

- **Producer**: ``sbws scanner``, once at startup.

- **Consumer**: ``sbws generate``, once each time it is ran.

Code: :class:`sbws.util.state.State`