Contributing to Simple Bandwidth Scanner
----------------------------------------

Thank you for your interest in Simple Bandwidth Scanner (sbws).

.. note::

    Simple Bandwidth Scanner is in the public domain according to its
    :doc:`CC0 license </LICENSE>`. No one has copyright over sbws, though we
    update the list of :doc:`authors </AUTHORS>` from time to time.


Pull requests are welcome, especially if they address open issues.

#. Fork the repo on GitHub
#. Clone a copy of sbws to your machine as per
   :doc:`the install instructions </INSTALL>`, but use your repo.
#. Fix that bug or implement that feature
    - As part of this process, it would be appreciated (and might event help
      you) if you wrote tests to catch the buggy behavior you're solving so it
      won't break again.
#. Make sure all tests pass when running ``tox``.
#. Commit your changes and push them to a branch in your sbws GitHub repo
#. Open a `pull request`_

We use flake8 to check some PEP8 errors/warnings. This will be checked with
``tox`` and Travis.

Simple Bandwidth Scanner is moving towards 100% test coverage. Please help us
reach that goal, or at least not move us away from it.

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

**Strongly prefer Unix timestamps or datetime objects in UTC** and always
work in UTC for as long as possible. When reading/writing/manipulating results
from some period of time in the past, always err on the side of caution. For
example, open an extra file into the past just in case it happens to include
result lines that have timestamps that are still considered valid (of course,
ignore results in the file that are no longer valid).

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
