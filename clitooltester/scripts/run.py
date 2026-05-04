#!/usr/bin/env python3
"""Script to run command line tool tests."""

import argparse
import logging
import sys

from clitooltester import test_runner


def Main():
    """Entry point of console script to run command line tool tests.

    Returns:
      int: exit code that is provided to sys.exit().
    """
    argument_parser = argparse.ArgumentParser(
        description="Runs command line tool tests."
    )
    argument_parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="enable debug output.",
    )
    argument_parser.add_argument(
        "configuration",
        nargs="?",
        action="store",
        metavar="PATH",
        default=None,
        help="path of the configuration file.",
    )
    options = argument_parser.parse_args()

    if not options.configuration:
        print("Configuration file missing.")
        print("")
        argument_parser.print_help()
        print("")
        return 1

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    runner = test_runner.TestRunner()

    runner.read_configuration(options.configuration)
    runner.run()

    return 0


if __name__ == "__main__":
    sys.exit(Main())
