.. _config_internal:

Internal code configuration files
==================================
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

.. literalinclude:: /examples/sbws.example.ini
    :caption: Example sbws.example.ini

**No other configuration files are read.**

.. _default-config:

Default Configuration
----------------------

.. literalinclude:: config.default.ini
    :caption: config.default.ini

.. _default-log-config:

If you know how to use
`Python's logging configuration file format`_,
then you can override or add to what is listed here by editing your config.ini.

.. literalinclude:: config.log.default.ini
    :caption: config.log.default.ini

.. _Python's logging configuration file format: https://docs.python.org/3.5/library/logging.config.html#logging-config-fileformat
