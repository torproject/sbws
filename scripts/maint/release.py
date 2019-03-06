#!/usr/bin/env python3
# Copyright 2019 juga (juga at riseup dot net), CC0 license.
"""Script to help release new versions.

It will:
0. Detect the current program version
1. Ask which version to release
2. Update the changelog automatically with ``gitchangelog``
   and leave the option to user to manually edit it
3. Modify the program version to release version,
   commit it and commit changelog
4. Create a version with the tag and sign it
5. Push the commit and tag to the repository
6. Obtain the release tarball from Github
7. Sign the release tarball
8. Modify the program to the next prerelease version and commit it
9. Push the commit

All in sequence and doesn't recover from any previous step.

It assumes that:
- the program version is in ``__init__.py.__version__``
- gitchangelog and semantic_version are installed
- we are in the master branch
- the remote repository to push is origin
- the next prerelease version is the release version + "-dev0"
- the official releases tarballs are in Github (because no access to dist.tpo)
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
    # Ensure this is a prerelease version (eg 1.0.3-dev0)
    assert version.prerelease
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


def replace_version(old_version, new_version):
    with open(sbws.__file__, 'r+') as f:
        text = f.read()
        text = re.sub(str(old_version), str(new_version), text)
        f.seek(0)
        f.write(text)
        f.truncate()


def obtain_next_prerelease_version(release_version):
    # Assuming that we are only jumping from release to `-dev0`
    next_prerelease_version = semantic_version.Version(
        str(release_version.next_patch()) + "-dev0"
        )
    return next_prerelease_version


def main(args):
    print(__doc__)
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

    print("\n3. Modify program version")
    print("--------------------------")
    print("\nReplacing __init__.py version with the release version...")
    replace_version(current_version, release_version)

    print("\nCommiting __init__.py and CHANGELOG.rst...")
    subprocess.call(['git', 'commit',
                     '-am', '"Release version {}."'.format(release_version)])

    print("\n4. Create tag and sign it")
    print("--------------------------")
    print("\nCreating the final tag and signing it...")
    subprocess.call(['git', 'tag', '-s', 'v{}'.format(release_version),
                     '-m', '"Release version {}."'.format(release_version)])

    print("\n5. Push commit and tag")
    print("----------------------")
    print("\nPush now so that the Github tarball will have the"
          " correct tag...")
    input("Press enter when you are sure everything is correct.")
    subprocess.call(['git', 'push', 'origin', 'master'])

    # While we use Github releases and not dist.tpo
    print("\n6. Create release tarball")
    print("-------------------------")
    print("Obtaining Github tarball...")
    subprocess.call(
        "torsocks wget https://github.com/torproject/sbws/archive/v{}.tar.gz"
        .format(release_version).split(' ')
        )

    print("\n7. Create the tarball signature")
    print("-------------------------------")
    print("Creating detached signature...")
    subprocess.call("gpg --default-key F305447AF806D46B "
                    "--output v{}.tar.gz.asc "
                    "--detach-sign v{}.tar.gz"
                    .format(release_version, release_version).split(' '))

    print("\nUpload the signature manually to Github.")
    input("Press enter when done.")
    print("\nRelease done!!!.")

    print("\n8. Create next prerelease version")
    print("---------------------------------")
    next_prerelease_version = obtain_next_prerelease_version(release_version)
    print("\nReplacing the version in the program with "
          "the next prerelease version...")
    replace_version(release_version, next_prerelease_version)

    print("\nCommitting the prerelease version...")
    subprocess.call(['git', 'commit',
                     '-am', '"Bump to {}."'.format(next_prerelease_version)])

    print("\n9. Push commit")
    print("--------------")
    input("Press enter when you are sure everything is correct.")
    subprocess.call(['git', 'push', 'origin', 'master'])
    print("Done!")


if __name__ == "__main__":
    main(sys.argv[1:])
