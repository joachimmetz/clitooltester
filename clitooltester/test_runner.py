"""Command line tool test runner."""

import subprocess


class TestRunner:
    """Runs a command line tool test."""

    def read_configuration(self, path):
        """Reads the configuration from a file.

        Args:
          path (str): path of the configuration file.
        """

    def run(self):
        """Runs a command line tool test."""
        arguments = [
            "docker",
            "run",
            "--network=none",
            "--quiet",
            "--read-only",
            "hello-world",
        ]
        result = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"[\033[91mFAIL\033[0m] {result.stderr:s}")
            return

        if result.stderr:
            print(f"[\033[91mFAIL\033[0m] unexpected output to stderr")
            print(result.stderr)
            return

        if "Hello from Docker!" not in result.stdout:
            print(f"[\033[91mFAIL\033[0m] unexpected output to stdout")
            print(result.stdout)
            return

        print(f"[\033[92mPASS\033[0m]")
