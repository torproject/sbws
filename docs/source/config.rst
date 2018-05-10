Simple Bandwidth Scanner Configuration Files
============================================

Sbws has four config files it reads: two general, and two specific to logging.
They all get combined internally to the same ``conf`` structure, so technically
you can put any option in any file, but you need to pay attention to the order
in which they are read. Options specified in multiple files will take the
values set in the last-read file. **It's best to only put options in the files
you are meant to put them in.**

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

Sbws then reads your custom config file. By default, after running ``sbws
init``, it is located in ``~/.sbws/config.ini``. Options in this
file overwrite options set in previously read config files.

Finally, sbws reads your custom logging config file. By default, after running
``sbws init``, it is located in ``~/.sbws/config.log.ini``. Options set in this file
overwrite options set in all other config files.

After running ``sbws init``, your ``~/.sbws/config.ini`` might look like this. Your
``~/.sbws/config.log.ini`` will be empty.

.. _init-config:

.. literalinclude:: config.ini
    :caption: Example ~/.sbws/config.ini

**No other configuration files are read.**

.. _default-config:

Default Config
--------------

.. literalinclude:: config.default.ini
    :caption: config.default.ini

.. _default-log-config:

.. literalinclude:: config.log.default.ini
    :caption: config.log.default.ini
