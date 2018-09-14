Contributing to Simple Bandwidth Scanner
=========================================

Thank you for your interest in Simple Bandwidth Scanner (``sbws``).

Examples of contributions include:

* Bug reports, feature requests
* Code/documentation patches

Bug reports
------------

Check that bug has not been already reported.
To report bugs or request features, open a ticket in
`Tor Project Trac <https://trac.torproject.org/projects/tor/newticket>`_
and assign the component to ``Core Tor``/``sbws``.

Code/documentation patches
---------------------------

The sbws canonical repository is https://gitweb.torproject.org/sbws.git,
but we review patches using the Github canonical repository
(https://github.com/torproject/sbws) Pull Requests (PR).

To know more about ``sbws`` code,

.. seealso::

  - :ref:`dev_doc`
  - ``./docs/source/testing.rst`` (or `testing </docs/source/testing.rst>`_
    or :ref:`testing`).
  - ``./docs/source/documenting.rst`` (or `documenting </docs/source/documenting.rst>`_
    or :ref:`documenting`).

The following are guidelines we aim to follow.

Steps to create a PR
~~~~~~~~~~~~~~~~~~~~~

1. Create a ticket in Tor Project Trac (:ref:`Open ticket <ticket-ref>`)
2. Clone ``sbws`` via the Github web interface
   https://github.com/torproject/sbws
3. Clone the repository locally
4. Install ``sbws`` as explained in ./INSTALL.rst and ./TESTING.rst
   Use ``pip install -e <>``
5. If needed install the documentation and build it as explained in
   ./DOCUMENTATION.rst
6. Create a new branch, named ``ticketXXX``.
   Optionally, name it with a string explaining what it does,
   ie ``ticketXXX_contributing``
7. Write code (:ref:`codestyle-ref`), tests, documentation,
   extra files (:ref:`extrafiles-ref`), commit (:ref:`commits-ref`), etc.
8. Ensure tests pass (./TESTING.rst).
9. Push your branch to your repository. If you have an account in Travis,
   you can see whether it pass the tests in Github and in
   https://travis-ci.org/youruser/sbws/
10. Create a PR from your branch to https://github.com/torproject/sbws
11. Change the Trac ticket status to ``needs_review``

.. _codestyle-ref:

Code style
~~~~~~~~~~

Follow the Zen of Python (:pep:`20`)

.. code-block:: pycon

    >>> import this
    The Zen of Python, by Tim Peters

    Beautiful is better than ugly.
    Explicit is better than implicit.
    Simple is better than complex.
    Complex is better than complicated.
    Flat is better than nested.
    Sparse is better than dense.
    Readability counts.

Code should adhere to the :pep:`8` guidelines.
Before release 1.0.0, some guidelines have not been followed,
such as the ordering the inputs (:pep:`8#imports`).

Any non-trivial change should contain tests. See ./TESTING.rst.
When running tests, currently ``flake8`` informs on some PEP8 errors/warnings,
but not all.

All functions, methods and classes should have :pep:`0257`
(except ``__repr__`` and ``__str__``).
Before release 1.0.0, some docstrigs do not have 3 double quotes ``"""``
(:pep:`0257#id15`).

New features should add a corresponding documentation.

Document your changes in ./CHANGELOG.rst following `keep a changelog`_.
Reference the Tor Project Trac ticket (example: ``#12345``) or
Github ticket (example: ``GH#123``).

Timestamps must be in UTC. It is prefered to use ``datetime`` objects or
Unix timestamps. Timestamps read by the user should be always formatted in
`ISO 8601 <https://en.wikipedia.org/wiki/ISO_8601>`_

Git workflow
------------

Commits
~~~~~~~~

Commit messages should follow the `Tim Pope`_ recommendations.

**Prefer a rebase workflow instead of merge**. Incorporating PRs should be done
with fast-forward merge, if easily possible. The larger the topic branch, the
harder this may be, so merge commits are allowed.

If, while working on a topic branch, some changes are made to master that
conflict with your work or that you need to incorporate into your work, **do
not merge master into your topic branch**; instead, rebase your topic branch on
top of master or cherry-pick the changes.

**Do not force push lightly** unless branches are clearly labeled as ones that
may get overwritten (for example: "transient\_" prefix). Instead of overwriting
a branch, add a version suffix (for example: "_02").



.. _pull request: https://github.com/pastly/simple-bw-scanner/compare

.. _tim pope: https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html

.. _`keep a changelog`: https://keepachangelog.com/en/1.0.0/
