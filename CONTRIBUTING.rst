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
  `Tor Project Trac <https://trac.torproject.org>`_
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

External link: `Code Style <https://docs.python-guide.org/writing/style/>`_

All functions, methods and classes should have :pep:`0257`
(except ``__repr__`` and ``__str__``).
Before release 1.0.0, some docstrigs do not have 3 double quotes ``"""``
(:pep:`0257#id15`).

External link: `Documentation <https://docs.python-guide.org/writing/documentation/>`_

New features should add a corresponding documentation in /docs.

An editor compatible with `EditorConfig <https://editorconfig.org/>`_ will
help you to follow the general formatting code style.

Timestamps must be in UTC. It is prefered to use ``datetime`` objects or
Unix timestamps. Timestamps read by the user should be always formatted in
`ISO 8601 <https://en.wikipedia.org/wiki/ISO_8601>`_

Functional style is prefered:

- use list comprenhensions lambda, map, reduce
- avoid reasigigning variables, instead create new ones
- use ``deepcopy`` when passing list of objects to a function/method
- classes should change attributes only in one method (other than __init__?)

[FUNC]_

In general, do not reinvent the wheel, use Python native modules as ``logging``,
instead of implementing similar functionality.
Or use other packages when the new dependency can be extra, for instance
`vulture`_.

.. _`extrafiles-ref`:

Extra required files
~~~~~~~~~~~~~~~~~~~~~

Any non-trivial change should contain tests. See ./TESTING.rst.
When running tests, currently ``flake8`` informs on some PEP8 errors/warnings,
but not all.

.. _commits-ref:

Commits
~~~~~~~~~

Each commit should reference the Tor Project Trac ticket (example: ``#12345``)
and possibly the bugfix version.

Try to make each commit a logically separate changes.::

  As a general rule, your messages should start with a single line that’s
  o more than about 50 characters and that describes the changeset concisely,
  followed by a blank line, followed by a more detailed explanation.
  The Git project requires that the more detailed explanation include
  your motivation for the change and contrast its implementation with
  previous behavior — this is a good guideline to follow.
  It’s also a good idea to use the imperative present tense in these messages.
  In other words, use commands.
  Instead of "I added tests for" or "Adding tests for," use "Add tests for."

[DIST]_

Template originally written by `Tim Pope`_: :ref:`example commit <commit-msg>`

Code being reviewed workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a PR is being reviewed, new changes might be needed:

- If the change does not modify a previous change, create new commits and push.
- If the change modifies a previous change and it's small,
  `git commit fixup <https://git-scm.com/docs/git-commit#Documentation/git-commit.txt---fixupltcommitgt>`_
  should be used. When it is agreed that the PR is ready, create a new branch
  named ``mybranch_02`` and run:

  .. code-block:: bash

    rebase --autosquash

  push, create new PR and close old PR mentioning the number of the new PR.
- If the review takes long and when it's ready code related to the PR has changed
  in master, create a new branch named ``mybranch_02`` and run:

  .. code-block:: bash

    rebase master

  push, create new PR and close old PR mentioning the number of the new PR.

[MERG]_

.. _review-ref:

Reviewing code
----------------

All code should be peer-reviewed. Two reasons for this are::

    Because a developer cannot think of everything at once;
    Because a fresh pair of eyes may spot an error, a corner-case in the code,
    insufficient documentation, a missing consistency check, etc.

[REVI]_

Reviewers:

- Should let the contributor know what to improve/change.
- Should not push code to the contributor's branch.
- Should wait for contributor's changes or feedback after changes are requested,
  before merging or closing a PR.
- Should merge (not rebase) the PR.
- If rebase is needed due to changes in master, the contributor should create
  a new branch named `xxx_rebased` based on the reviewed branch, rebase and
  create a new PR from it, as explained above.
- If new changes are needed when the contributor's branch is ready to merge,
  the reviewer can create a new branch based on the contributor's branch,
  push the changes and merge that PR.
  The contributor should be notified about it.
- If the reviewer realize that new changes are needed after the PR has been
  merged, the reviewer can push to master, notifying the contributor about the
  changes.
- Because currently there are not many reviewers, reviewers can merge their own
  PR if there was not any feedback after a week.
- Should not push directly to master, unless changes are trivial (typos,
  extra spaces, etc.)
- Should not push to master new features while there are open PRs to review.

Currently, the reviewers are the persons that have contributed to the code:
pastly, teor, juga.

.. _releases-ref:

Releases
----------

Releases follow `semantic versioning`_.
Until release 1.0.0 is reached, this project is not considered production
ready.

Currently development happens in master, this might change from release 1.0.0

so that master has the last release changes, and development happens in the
next release branch.

Before major releases, ensure that:

- Installation from scratch, as specified in ./INSTALL.md, must success.
- All tests must pass.
- Tor must be able to parse the produced bw files
  (current way is manual)

  .. todo::

    Test that run Tor as dirauth and parse the files

- Bandwidth files must produce graphs compatible with Torflow
  (current way to test it is manual)

  .. todo::

    Implement something to compare error with current consensus.
- A dirauth should be able to understand the documentation, otherwise the
  documentation should be clarified.

.. _changelog:

Create a ./CHANGELOG.rst file.
Each entry should reference the Tor Project Trac ticket (example: ``#12345``)
and possibly the bugfix version.
Until version 1.0.2 we have followed `keep a changelog`_ format.

.. _commit-msg:

Example commit message
-----------------------

::

  Short (50 chars or less) summary of changes

  More detailed explanatory text, if necessary.  Wrap it to
  about 72 characters or so.  In some contexts, the first
  line is treated as the subject of an email and the rest of
  the text as the body.  The blank line separating the
  summary from the body is critical (unless you omit the body
  entirely); tools like rebase can get confused if you run
  the two together.

  Further paragraphs come after blank lines.

    - Bullet points are okay, too

    - Typically a hyphen or asterisk is used for the bullet,
      preceded by a single space, with blank lines in
      between, but conventions vary here


.. rubric:: External eferences

.. [DIST] https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project
.. [MERG] https://www.atlassian.com/git/tutorials/merging-vs-rebasing
.. [REVI] https://doc.sagemath.org/html/en/developer/reviewer_checklist.html
.. [FUNC] https://medium.com/@rohanrony/functional-programming-in-python-1-lambda-map-filter-reduce-zip-8739ea144186
.. _tim pope: https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
.. _`keep a changelog`: https://keepachangelog.com/en/1.0.0/
.. _`semantic versioning`: https://semver.org/
.. _`vulture`: https://pypi.org/project/vulture/
