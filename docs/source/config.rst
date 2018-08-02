Simple Bandwidth Scanner Configuration Files
============================================

How to create user customized configuration files
--------------------------------------------------
``sbws`` use internal configuration files.
These are **not** intented to be modified by a user.
If a user needs a customized configuration file, the user needs to create it.
There's an example configuration file with the minimum data that a user
probably needs to edit in ``examples``. For more advanced configuration options see
documentation below.
``sbws`` will check by default whether there's a user customized file in
``~/.sbws.ini`` and use it when it exists.
The user can store a customized configuration file anywhere else in the file
system and and provide ``sbws`` with the path to it via the ``-c`` or
``--config`` cli option.

How sbws configuration works internally
----------------------------------------
Sbws has two default config files it reads: on general, and one specific to
logging.
They all get combined internally to the same ``conf`` structure.

It first reads the config file containing the default values for almost all
options. If you installed sbws in a virtual environment located at /tmp/venv,
then you will probably find the ``config.default.ini`` in a place such as
``/tmp/venv/lib/python3.5/site-packages/sbws/`` **You should never edit this
file**.  The contents of this default config file can be found :ref:`at the
bottom of this page <default-config>`.

Second, ``sbws`` will read ``config.log.default.ini``. It will be located in
the same place as the previous file, and **should not be edited** like the
previous file. The contents of this default log config file can be found
:ref:`at the bottom of this page <default-log-config>`. Options set here
overwrite options set in the previous config file.

Sbws then reads your custom config file. By default, it will search for it
in ``~/.sbws.ini``. Options in this file overwrite options set in previously
read config files.

The user example config file provided by ``sbws`` might look like this.

.. _init-config:

.. literalinclude:: config.example.ini
    :caption: Example config.example.ini

**No other configuration files are read.**

.. _default-config:

Default Config
--------------

.. literalinclude:: config.default.ini
    :caption: config.default.ini

.. _default-log-config:

If you know how to use
`Python's logging configuration file format`_,
then you can override or add to what is listed here by editing your config.ini.

.. literalinclude:: config.log.default.ini
    :caption: config.log.default.ini

.. _Python's logging configuration file format: https://docs.python.org/3.5/library/logging.config.html#logging-config-fileformat
