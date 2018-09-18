.. _contributing:

Contributing to Simple Bandwidth Scanner
=========================================

Thank you for your interest in Simple Bandwidth Scanner (``sbws``).

Examples of contributions include:

* Bug reports, feature requests
* Code/documentation patches

Bug reports or feature requests
---------------------------------

* Check that it has not been already reported.

.. _ticket-ref:

* Open a ticket in
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

Workflow
~~~~~~~~~

In general, when you are modifying code that was not wrotten by yourself,
try to keep changes to the minimum.

When a PR is being reviewed, new changes might be needed:

- If the change does not modify a previous change, just commit and push.
- If the change modifies a previous change and it's small,
  `git commit fixup <https://git-scm.com/docs/git-commit#git-commit---fixupltcommitgt>`_
  should be used. When it is agreed that the PR is ready, create a new branch
  named ``mybranch_02`` and run::

    rebase --autosquash

  push, create new PR and close old PR mentioning the number of the new PR.
- If the review takes long and when it's ready code related to the PR has changed
  in master, create a new branch named ``mybranch_02`` and run::

    rebase master

  push, create new PR and close old PR mentioning the number of the new PR.

Reviewers: (see :ref:`reviewers`)

- should not push code to your branch, unless you agree
- should let you know when new changes are needed
- should not merge your PR after changes are requested and you notify you did
  via the PR or the ticket.
- should not merge your PR and then inmediatly modify your code pushing
  directly to master without informing you previously and without your consent.

.. _reviewers:

Reviewers
----------

At the moment, there is not any policy to decide who the reviewers are.
They are the current people that has contributed to this code: pastly, teor,
juga0.
They should not push directly to master and they should peer-review their code.
Currently, if a PR from a reviewer has not been peer-reviewd by other reviewer
in a week, the reviewer can merge their/her/his own PR.

They should merge PR to master. Instead of rebase. If needed, rebase should be
done by the contributor before the merge.

.. _tim pope: https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html

.. _`keep a changelog`: https://keepachangelog.com/en/1.0.0/
