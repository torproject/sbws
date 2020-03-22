#!/usr/bin/env python3
""""""
import argparse

from sbws.lib.bwfile_health import BwFile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file-path", help="Banwidth file path.")

    args = parser.parse_args()

    header_health = BwFile.load(args.file_path)
    header_health.report


if __name__ == "__main__":
    main()
