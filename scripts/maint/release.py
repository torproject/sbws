#!/usr/bin/env python3
"""Script to help release new versions."""
import sys


def main(args):
    version = args[0]
    print("# This script will guide you to create a new release, but it will "
          "not do anything.")
    print("# ================================================================")
    print("# Install gitchangelog in a virtualenv:")
    print("pip install gitchangelog")
    print("# Create a tag so that gitchangelog will create the new section "
          "with the correct new tag:")
    print("git tag {}".format(version))
    print("# Update the changelog:")
    print("gitchangelog")
    print("# Edit the changelog!")
    print("# Remove the tag:")
    print("git tag -d {}".format(version))
    print("# Replace the new version in __init__.py:")
    print("# Commit __init__.py and CHANGELOG.rst with Release message:")
    print("git commit -a -m 'Release {}'".format(version))
    print("# Create the final tag and sign it:")
    print("git tag -s v{}".format(version))
    print("# Push now so that the Github tarball will have the correct tag.")
    print("git push")
    print("# Obtain Github tarball:")
    print("torsocks wget "
          "https://github.com/torproject/sbws/archive/v{}.tar.gz")
    print("# Create the tarball signature:")
    print("gpg --default-key F305447AF806D46B --detach-sign v{}.tar.gz  "
          "--output v{}.tar.gz.asc")
    print("# Upload the signature manually to Github.")
    print("# Now bump to the next development version:")
    print("# Replace the version in __init__.py with the next version -dev0")
    print("# Commit the development version:")
    print("git commit -a -m 'Bump to version X'")
    print("# Done!")


if __name__ == "__main__":
    main(sys.argv[1:])
