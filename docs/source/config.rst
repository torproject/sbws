Simple Bandwidth Scanner Configuration Files
============================================

Sbws has two config files it reads.

It first reads the config file containing the default values for almost all
options. If you installed sbws in a virtual environment located at /tmp/venv,
then you will probably find the ``config.default.ini`` in a place such as
``/tmp/venv/lib/python3.5/site-packages/sbws/`` **You should never edit this
file**.  The contents of this default config file can be found :ref:`at the
bottom of this page <default-config>`.

Sbws then reads your custom config file. By default, after running ``sbws
init``, it is located in ``~/.sbws/config.ini``. A configuration option in this
file overwrites the default file found in the default file.

After running ``sbws init``, your ``~/.sbws/config.ini`` might look like this.

.. _init-config:

.. literalinclude:: config.ini
    :caption: Example ~/.sbws/config.ini

**No other configuration files are read.** The only files that are read are the
``config.default.ini`` file located in a place the user shouldn't touch, and
the ``config.ini`` in their ``.sbws`` directory.


.. _default-config:

Default Config
--------------

.. literalinclude:: config.default.ini
    :caption: config.default.ini
