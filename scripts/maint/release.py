#!/usr/bin/env python3
# Copyright 2019 juga (juga at riseup dot net), CC0 license.
"""Script to help release new versions.

usage: release.py GPG_KEY_IDENTIFIER

It will:
0. Detect the current program version
1. Ask which version to release
2. Update the changelog automatically with ``gitchangelog``
   and leave the option to user to manually edit it
3. Commit the changelog
4. Create a version with the tag and sign it
5. Push the commit and tag to the repository
6. Obtain the release tarball
7. Sign the release tarball
8. Modify the program to the next prerelease version and commit it
9. Push the commit

All in sequence and doesn't recover from any previous step.

It assumes that:
- gitchangelog and semantic_version are installed
- the program version can be obtained with ``sbws.__version__``
- the official tarball releases are at gitlab.torproject.org
- the key to sign the release is only one and is available in the system

"""
import re
import subprocess
import sys
try:
    import semantic_version
except ImportError:
    print("Please, install semantic_version")
    sys.exit(1)
try:
    import gitchangelog  # noqa
except ImportError:
    print("Please, install gitchangelog")
    sys.exit(1)

import sbws


def obtain_release_version(version):
    release_type_dict = {
        1: version.next_patch(),
        2: version.next_minor(),
        3: version.next_major(),
    }
    print("Current prerelease version: ", version)
    print("which version would you like to release?:")
    print("1. to patch release: ", release_type_dict[1])
    print("2. to minor release: ", release_type_dict[2])
    print("3. to major release: ", release_type_dict[3])
    release_type = int(input())
    try:
        return release_type_dict[release_type]
    except KeyError:
        print("Invalid release.")
        sys.exit(1)


def main(args):
    print(__doc__)
    try:
        keyid = args[0]
    except IndexError:
        print("Please, pass a GPG key identifier as argument.")
        sys.exit(1)
    print("1. Which version to release")
    print("---------------------------")
    current_version = semantic_version.Version(sbws.__version__)
    release_version = obtain_release_version(current_version)

    print("\n2. Update changelog")
    print("-------------------")
    print("Creating tag v{} so that gitchangelog will create the new section "
          "with the correct new tag...".format(release_version))
    subprocess.call(['git', 'tag', 'v{}'.format(release_version),
                     '-m', '\"Release version {}.\"'.format(release_version)])

    print("\nUpdating the changelog automatically...")
    subprocess.call('gitchangelog'.split(' '))

    print("\nEdit the changelog manually to remove merge commits and "
          "leave only the apropiate paragraph for every bug/feature.")
    input("Press enter when done.\n")

    print("\nRemoving the tag...")
    subprocess.call(['git', 'tag', '-d', 'v{}'.format(release_version)])

    print("\n3. Commit the changelog")
    print("--------------------------")
    print("\nCommiting CHANGELOG.rst...")
    subprocess.call(['git', 'commit',
                     '-am', '"Release version {}."'.format(release_version)])

    print("\n4. Create tag and sign it")
    print("--------------------------")
    print("\nCreating the final tag and signing it...")
    subprocess.call(['git', 'tag', '-s', 'v{}'.format(release_version),
                     '-m', '"Release version {}."'.format(release_version)])

    print("\n5. Push commit and tag")
    print("------------------------")
    print("\nPush now so that the Gitlab creates the tarball from the new "
          " commit and tag, eg:")
    print("git push myremote mybranch")
    print("git push myremote --tags")
    input("Press enter when you are done.")

    print("\n6. Obtain the release tarball")
    print("-------------------------------")
    print("Obtaining Gitlab tarball...")
    subprocess.call(
        "wget https://gitlab.torproject.org/tpo/network-health/sbws/-/archive/v{}/sbws-v{}.tar.gz "
        "-O v{}.tar.gz"
        .format(release_version, release_version, release_version).split(' ')
        )

    print("\n7. Create the tarball signature")
    print("-------------------------------")
    print("Creating detached signature...")
    subprocess.call("gpg --default-key {} "
                    "--output v{}.tar.gz.asc "
                    "--detach-sign v{}.tar.gz"
                    .format(keyid, release_version, release_version)
                    .split(' '))

    print("\nUpload the signature manually to Gitlab.")
    input("Press enter when done.")
    print("\nRelease done!!!.")

    print("\n8. Create next prerelease branch")
    print("----------------------------------")
    print("\nIf this release happens in a maintainance branch, merge the "
          "the commit to master and push, eg:"
          "git checkout master"
          "git merge --no-ff mybranch"
          "git push myremote master")
    next_branch_version = "maint{}".format(release_version)
    print("And create the next prerelease branch, eg:")
          "git checkout -b {}".format(next_branch_version)


if __name__ == "__main__":
    main(sys.argv[1:])
