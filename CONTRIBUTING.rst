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

Timestamps must be in UTC. It is prefered to use ``datetime`` objects or
Unix timestamps. Timestamps read by the user should be always formatted in
`ISO 8601 <https://en.wikipedia.org/wiki/ISO_8601>`_

Git and GitHub Guidelines
=========================

**Write good commit messages** that at least follow the spirit of
:ref:`this example <commit-msg>`.

Strive to **write many small commits** each containing an atomic change instead
of one large mega-commit. This not only makes code review easier, but it also
makes commits that show up in ``git blame`` 10 years from now make more sense.

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

Coding Guidelines
=================


**Document your addition, fix, change, or whatever in the changelog**. See
`keep a changelog`_ for the standard we follow. Of note, add Added, Changed,
Deprecated, Removed, Fixed, and Security headings as needed in the Unreleased
section. **If your change has a trac or GitHub ticket, reference it** like
``(GH#123)`` or ``(trac#22104)``. When it comes time to do a release, the
person doing the release should (1) change the name of the Unreleased section
and add a new one, and (2) update the links at the bottom.


.. _commit-msg:

Example commit message
======================

With thanks to `Tim Pope`_:


::

    Capitalized, short (50 chars or less) summary

    More detailed explanatory text, if necessary.  Wrap it to about 72
    characters or so.  In some contexts, the first line is treated as the
    subject of an email and the rest of the text as the body.  The blank
    line separating the summary from the body is critical (unless you omit
    the body entirely); tools like rebase can get confused if you run the
    two together.

    Write your commit message in the imperative: "Fix bug" and not "Fixed bug"
    or "Fixes bug."  This convention matches up with commit messages generated
    by commands like git merge and git revert.

    Further paragraphs come after blank lines.

    - Bullet points are okay, too

    - Typically a hyphen or asterisk is used for the bullet, followed by a
      single space, with blank lines in between, but conventions vary here

    - Use a hanging indent



.. _pull request: https://github.com/pastly/simple-bw-scanner/compare

.. _tim pope: https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html

.. _`keep a changelog`: https://keepachangelog.com/en/1.0.0/
