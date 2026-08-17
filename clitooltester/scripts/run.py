#!/usr/bin/env python3
"""Script to run command line tool tests."""

import argparse
import sys

from clitooltester import results_log
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
        "-i",
        "--inputs",
        dest="inputs",
        action="store",
        default=None,
        help="path of the inputs configuration file.",
    )
    argument_parser.add_argument(
        "--input_sets",
        "--input-sets",
        dest="input_sets",
        action="store",
        default=None,
        help="comma separated list of names of the inputs sets to use.",
    )
    argument_parser.add_argument(
        "-j",
        "--jobs",
        dest="jobs",
        action="store",
        type=int,
        default=1,
        help="number of parallel jobs, where 1 represent sequential.",
    )
    argument_parser.add_argument(
        "-l",
        "--log",
        dest="log_file",
        action="store",
        default=None,
        help="path to write test results log file.",
    )
    argument_parser.add_argument(
        "--no_stdout",
        "--no-stdout",
        dest="verbose_stdout",
        action="store_false",
        default=True,
        help="do not show stdout in verbose output.",
    )
    argument_parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="enable verbose output.",
    )
    argument_parser.add_argument(
        "--write_references",
        "--write-references",
        dest="write_references",
        action="store_true",
        default=False,
        help="write normalized stdout to reference file if it does not exist.",
    )
    argument_parser.add_argument(
        "configuration",
        nargs="?",
        action="store",
        metavar="PATH",
        default=None,
        help="path of the test configuration file.",
    )
    options = argument_parser.parse_args()

    if not options.configuration:
        print("Test configuration file missing.")
        print("")
        argument_parser.print_help()
        print("")
        return 1

    if options.jobs <= 0:
        print(f"Unsupported number of jobs: {options.jobs:d}")
        return 1

    verbose_stdout = options.verbose and options.verbose_stdout
    verbose_stderr = options.verbose

    runner = test_runner.TestRunner(
        verbose_stderr=verbose_stderr,
        verbose_stdout=verbose_stdout,
        write_references=options.write_references,
    )
    try:
        test_definition = runner.ReadTestConfiguration(options.configuration)
    except (FileNotFoundError, IOError, RuntimeError) as exception:
        print(
            f"Unable to read test configuration file: '{options.configuration:s}' "
            f"with error: {exception!s}"
        )
        return 1

    if test_definition.package and getattr(test_definition.package, "build"):
        if runner.BuildPackage(test_definition) != 0:
            print("\033[31mERROR: build failed\033[0m")
            return 1

    if test_definition.docker and getattr(test_definition.docker, "dockerfile"):
        if runner.BuildDockerImage(test_definition) != 0:
            print("\033[31mERROR: docker build failed\033[0m")
            return 1

    if not options.inputs:
        test_results = runner.RunTests(test_definition, jobs=options.jobs)
    else:
        sets_to_include = None
        if options.input_sets:
            sets_to_include = set(options.input_sets.split(","))
        test_inputs = runner.ReadInputsConfiguration(
            options.inputs, sets_to_include=sets_to_include
        )
        test_results = runner.RunTests(
            test_definition, jobs=options.jobs, test_inputs=test_inputs
        )

    number_of_tests = len(test_results)
    number_of_failed_tests = sum(1 for result in test_results if not result.success)

    if options.log_file:
        log_file = results_log.ResultsLog(options.log_file)
        log_file.Write(test_results)

    print("\nTest results.\n")

    if number_of_failed_tests != 0:
        if number_of_tests == 1:
            print(
                f"\033[31mERROR: 1 test was run,\n{number_of_failed_tests:d} failed "
                f"unexpectedly.\033[0m"
            )
        else:
            print(
                f"\033[31mERROR: All {number_of_tests:d} tests were run,\n"
                f"{number_of_failed_tests:d} failed unexpectedly.\033[0m"
            )
        return 1

    if number_of_tests == 1:
        print("\033[32m1 test was successful.\033[0m")
    else:
        print(f"\033[32mAll {number_of_tests:d} tests were successful.\033[0m")

    return 0


if __name__ == "__main__":
    sys.exit(Main())
