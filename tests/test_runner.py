#!/usr/bin/env python3
"""Tests of the command line tool test runner."""

import gzip
import os
import tempfile
import unittest

from unittest import mock

from clitooltester import resources
from clitooltester import test_runner

from tests import test_lib


class TestRunnerTest(test_lib.BaseTestCase):
    """Tests the command line tool test runner."""

    # pylint: disable=protected-access

    def testNormalizeStdout(self):
        """Tests _NormalizeStdout function."""
        runner = test_runner.TestRunner(quiet=True)

        with tempfile.TemporaryDirectory() as temporary_directory:
            normalizer = os.path.join(temporary_directory, "normalizer.py")
            with open(normalizer, "w", encoding="utf-8") as file_object:
                file_object.write(
                    "import sys\n\nsys.stdout.write(sys.stdin.read().strip())\n"
                )

            run_step_result = runner._NormalizeStdout(
                normalizer,
                gzip.compress(b"hello world\n"),
            )
            self.assertEqual(run_step_result.get_exit_code(), 0)
            self.assertEqual(
                gzip.decompress(run_step_result.get_output()), b"hello world"
            )
            self.assertEqual(gzip.decompress(run_step_result.get_error_message()), b"")

        # Test with nonexistent normalization script
        run_step_result = runner._NormalizeStdout(
            "/nonexistent/script.py",
            gzip.compress(b"hello world\n"),
        )
        self.assertEqual(run_step_result.get_exit_code(), 1)
        self.assertEqual(gzip.decompress(run_step_result.get_output()), b"")
        self.assertEqual(
            gzip.decompress(run_step_result.get_error_message()),
            b"Missing normalizer: /nonexistent/script.py",
        )

    def testProcessStdout(self):
        """Tests _ProcessStdout function."""
        # Test without a normalize, validator and reference_file
        runner = test_runner.TestRunner(quiet=True)

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"

        test_definition = resources.TestDefinition()
        test_definition.name = "test"
        test_definition.command = "ls %input%"
        test_definition.package = package
        test_definition.stdout = resources.StdoutDefinition()

        test_result = resources.TestResult()
        test_result.stdout = "some output"

        runner._ProcessStdout(test_definition, test_result, {})

        self.assertEqual(test_result.stdout, "some output")

    @mock.patch("clitooltester.test_runner.subprocess.run")
    @mock.patch("clitooltester.test_runner.shutil.which")
    def testRunTestWithDocker(self, mock_shutil_which, mock_subprocess_run):
        """Tests the _RunTestWithDocker function."""
        runner = test_runner.TestRunner(quiet=True)

        mock_shutil_which.return_value = "/usr/bin/docker"

        # Test with subprocess.run success
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        docker = resources.DockerDefinition()
        docker.tag = "myimage:latest"

        test_definition = resources.TestDefinition()
        test_definition.name = "my_test"
        test_definition.command = "ls /input"
        test_definition.docker = docker

        test_result = runner._RunTestWithDocker(test_definition)
        self.assertEqual(test_result.exit_code, 0)

        # Test with input and subprocess.run success
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        docker = resources.DockerDefinition()
        docker.tag = "myimage:latest"

        test_definition = resources.TestDefinition()
        test_definition.name = "my_test"
        test_definition.command = "ls %input%"
        test_definition.docker = docker

        test_input = resources.InputDefinition()
        test_input.name = "test_input"
        test_input.path = "/some/path/data.bin"

        test_result = runner._RunTestWithDocker(test_definition, test_input=test_input)
        self.assertEqual(test_result.exit_code, 0)

        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0][0]
        self.assertIn("-v", call_args)

        if os.name == "posix":
            self.assertIn("/input/data.bin", call_args)
        else:
            self.assertIn('"/input/data.bin"', call_args)

        # Test with input set and subprocess.run success
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        docker = resources.DockerDefinition()
        docker.tag = "myimage:latest"

        test_definition = resources.TestDefinition()
        test_definition.name = "my_test"
        test_definition.command = "ls %input%"
        test_definition.docker = docker

        test_input = resources.InputDefinition()
        test_input.name = "ext/ext2"
        test_input.path = "/mnt/hdd/test_data/ext/ext2.raw"

        test_result = runner._RunTestWithDocker(test_definition, test_input=test_input)
        self.assertEqual(test_result.exit_code, 0)

        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0][0]
        self.assertIn("-v", call_args)

        if os.name == "posix":
            self.assertIn("/input/ext2.raw", call_args)
        else:
            self.assertIn('"/input/ext2.raw"', call_args)

        # Test with missing configuration
        mock_subprocess_run.reset_mock()

        test_definition = resources.TestDefinition()
        test_definition.name = "test"
        test_definition.command = "mycommand"
        test_definition.docker = None

        with self.assertRaises(ValueError):
            runner._RunTestWithDocker(test_definition)

        # Test with subprocess.run failure
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "stdout output\n"
        mock_result.stderr = "stderr output\n"
        mock_subprocess_run.return_value = mock_result

        docker = resources.DockerDefinition()
        docker.tag = "myimage:latest"

        test_definition = resources.TestDefinition()
        test_definition.name = "my_test"
        test_definition.command = "ls /input"
        test_definition.docker = docker

        test_result = runner._RunTestWithDocker(test_definition)
        self.assertEqual(test_result.exit_code, 1)

    @mock.patch("clitooltester.test_runner.subprocess.run")
    def testRunTestWithPackageSuccess(self, mock_subprocess_run):
        """Tests the _RunTestWithPackage function."""
        runner = test_runner.TestRunner(quiet=True)

        # Test with subprocess.run success
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"

        test_definition = resources.TestDefinition()
        test_definition.name = "my_test"
        test_definition.command = "tool"
        test_definition.package = package

        test_result = runner._RunTestWithPackage(test_definition)
        self.assertEqual(test_result.exit_code, 0)

        # Test with input and subprocess.run success
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"

        test_definition = resources.TestDefinition()
        test_definition.name = "my_test"
        test_definition.command = "tool %input%"
        test_definition.package = package

        test_input = resources.InputDefinition()
        test_input.name = "data"
        test_input.path = "/data/file.bin"

        test_result = runner._RunTestWithPackage(test_definition, test_input=test_input)
        self.assertEqual(test_result.exit_code, 0)

        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0][0]

        if os.name == "posix":
            self.assertIn("/data/file.bin", call_args)
        else:
            self.assertIn('"/data/file.bin"', call_args)

        # TODO: Test with input set and subprocess.run success

        # Test with subprocess.run failure
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "stdout output\n"
        mock_result.stderr = "stderr output\n"
        mock_subprocess_run.return_value = mock_result

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"

        test_definition = resources.TestDefinition()
        test_definition.name = "my_test"
        test_definition.command = "command"
        test_definition.package = package

        test_result = runner._RunTestWithPackage(test_definition)
        self.assertEqual(test_result.exit_code, 1)

    def testSubstituteInputPlaceholder(self):
        """Tests the _SubstitutePlaceholders function."""
        runner = test_runner.TestRunner(quiet=True)

        # Test with %input%
        command = "%input%"
        test_values = {"%input%": "/input/test.raw"}

        result = runner._SubstitutePlaceholders(command, test_values)
        self.assertEqual(result, "/input/test.raw")

        # Test with %package%
        command = "%package%/scripts/analyze.py"
        test_values = {"%package%": "/home/user/pkg"}

        result = runner._SubstitutePlaceholders(command, test_values)
        self.assertEqual(result, "/home/user/pkg/scripts/analyze.py")

        # Test with %input% and %package%
        command = "%package%/tool %input%"
        test_values = {"%package%": "/home/user/pkg", "%input%": "/input/data"}

        result = runner._SubstitutePlaceholders(command, test_values)
        self.assertEqual(result, "/home/user/pkg/tool /input/data")

        # Test without placeholders
        command = "ls -la"
        test_values = {}

        result = runner._SubstitutePlaceholders(command, test_values)
        self.assertEqual(result, "ls -la")

        # Test with unsupported placeholder
        command = "%input%/other.txt"
        test_values = {"%in%": "partial"}

        result = runner._SubstitutePlaceholders(command, test_values)
        self.assertEqual(result, "%input%/other.txt")

        # Test with multiple occurrences of %input%
        command = "%input% and %input%"
        test_values = {"%input%": "/path"}

        result = runner._SubstitutePlaceholders(command, test_values)
        self.assertEqual(result, "/path and /path")

    def testValidateStdout(self):
        """Tests _ValidateStdout function."""
        runner = test_runner.TestRunner(quiet=True)

        validator_script = (
            "import sys\n"
            "\n"
            "with open(sys.argv[1], encoding='utf-8') as f:\n"
            "    reference = f.read()\n"
            "\n"
            "input = sys.stdin.read()\n"
            "\n"
            "if input != reference:\n"
            "    print('Mismatch')\n"
            "    sys.exit(1)\n"
            "\n"
            "print('Match')\n"
            "sys.exit(0)\n"
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            validator = os.path.join(temporary_directory, "validator.py")
            with open(validator, "w", encoding="utf-8") as file_object:
                file_object.write(validator_script)

            reference_file = os.path.join(temporary_directory, "reference.txt")
            with open(reference_file, "w", encoding="utf-8") as file_object:
                file_object.write("hello world\n")

            run_step_result = runner._ValidateStdout(
                validator,
                reference_file,
                gzip.compress(b"hello world\n"),
            )
            self.assertEqual(run_step_result.get_exit_code(), 0)
            self.assertEqual(gzip.decompress(run_step_result.get_output()), b"Match\n")
            self.assertEqual(gzip.decompress(run_step_result.get_error_message()), b"")

        # Test with validation failure
        with tempfile.TemporaryDirectory() as temporary_directory:
            validator = os.path.join(temporary_directory, "validator.py")
            with open(validator, "w", encoding="utf-8") as file_object:
                file_object.write(validator_script)

            reference_file = os.path.join(temporary_directory, "reference.txt")
            with open(reference_file, "w", encoding="utf-8") as file_object:
                file_object.write("hello universe\n")

            run_step_result = runner._ValidateStdout(
                validator,
                reference_file,
                gzip.compress(b"hello world\n"),
            )
            self.assertEqual(run_step_result.get_exit_code(), 1)
            self.assertEqual(
                gzip.decompress(run_step_result.get_output()), b"Mismatch\n"
            )
            self.assertEqual(gzip.decompress(run_step_result.get_error_message()), b"")

        # TODO: Test with nonexistent validation script
        # TODO: Test with nonexistent reference file

    @mock.patch("clitooltester.test_runner.subprocess.run")
    @mock.patch("clitooltester.test_runner.os.environ")
    def testBuildPackage(self, mock_environ, mock_subprocess_run):
        """Tests the BuildPackage function."""
        runner = test_runner.TestRunner(quiet=True)

        mock_environ.get.return_value = "/bin/bash"

        # Test with subprocess.run success
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"
        package.build = "make install"
        package.build_env = None
        test_definition = resources.TestDefinition()
        test_definition.package = package

        result = runner.BuildPackage(test_definition)
        self.assertEqual(result, 0)

        # Test with build_env and subprocess.run success
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"
        package.build = "build.sh"
        package.build_env = {"CC": "clang"}
        test_definition = resources.TestDefinition()
        test_definition.package = package

        result = runner.BuildPackage(test_definition)
        self.assertEqual(result, 0)

        mock_subprocess_run.assert_called_once()
        call_kwargs = mock_subprocess_run.call_args[1]
        self.assertEqual(call_kwargs["env"]["CC"], "clang")
        self.assertEqual(call_kwargs["cwd"], "/home/user/pkg")

        # Test with missing configuration
        mock_subprocess_run.reset_mock()

        test_definition = resources.TestDefinition()
        test_definition.package = None

        with self.assertRaises(ValueError):
            runner.BuildPackage(test_definition)

        # Test with subprocess.run failure
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "build stdout\n"
        mock_result.stderr = "build stderr\n"
        mock_subprocess_run.return_value = mock_result

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"
        package.build = "make install"
        package.build_env = None
        test_definition = resources.TestDefinition()
        test_definition.package = package

        result = runner.BuildPackage(test_definition)
        self.assertEqual(result, 1)

    @mock.patch("clitooltester.test_runner.subprocess.run")
    @mock.patch("clitooltester.test_runner.shutil.which")
    def testBuildDocker(self, mock_shutil_which, mock_subprocess_run):
        """Tests the BuildDockerImage function."""
        runner = test_runner.TestRunner(quiet=True)

        mock_shutil_which.return_value = "/usr/bin/docker"

        # Test with subprocess.run success
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        docker = resources.DockerDefinition()
        docker.tag = "myimage:latest"
        docker.dockerfile = "Dockerfile"

        test_definition = resources.TestDefinition()
        test_definition.docker = docker

        result = runner.BuildDockerImage(test_definition)
        self.assertEqual(result, 0)

        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0][0]
        self.assertIn("myimage:latest", call_args)
        self.assertIn("Dockerfile", call_args)

        # Test with subprocess.run failure
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "docker stdout\n"
        mock_result.stderr = "docker stderr\n"
        mock_subprocess_run.return_value = mock_result

        docker = resources.DockerDefinition()
        docker.tag = "myimage:latest"
        docker.dockerfile = "Dockerfile"

        test_definition = resources.TestDefinition()
        test_definition.docker = docker

        result = runner.BuildDockerImage(test_definition)
        self.assertEqual(result, 1)

        # Test with missing configuration
        mock_subprocess_run.reset_mock()

        test_definition = resources.TestDefinition()
        test_definition.docker = None

        with self.assertRaises(ValueError):
            runner.BuildDockerImage(test_definition)

        # Test with missing dockerfile
        mock_subprocess_run.reset_mock()

        docker = resources.DockerDefinition()
        docker.tag = "myimage:latest"
        docker.dockerfile = None

        test_definition = resources.TestDefinition()
        test_definition.docker = docker

        with self.assertRaises(ValueError):
            runner.BuildDockerImage(test_definition)

    def testReadInputsConfiguration(self):
        """Tests the ReadInputsConfiguration function."""
        runner = test_runner.TestRunner(quiet=True)

        test_file_path = self._GetTestFilePath(["inputs.yaml"])
        self._SkipIfPathNotExists(test_file_path)

        inputs = runner.ReadInputsConfiguration(test_file_path)

        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0].name, "ext2")

        # Test with input set
        test_file_path = self._GetTestFilePath(["inputs_with_set.yaml"])
        self._SkipIfPathNotExists(test_file_path)

        inputs = runner.ReadInputsConfiguration(test_file_path)

        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0].name, "ext/ext2")

    def testReadTestConfiguration(self):
        """Tests the ReadTestConfiguration function."""
        runner = test_runner.TestRunner(quiet=True)

        test_file_path = self._GetTestFilePath(["test.yaml"])
        self._SkipIfPathNotExists(test_file_path)

        result = runner.ReadTestConfiguration(test_file_path)

        self.assertEqual(result.name, "dfimagetools_recursive_hasher")
        self.assertIsNotNone(result.package)

        # Test with missing definitions
        with tempfile.TemporaryDirectory() as temporary_directory:
            test_file_path = os.path.join(temporary_directory, "test.yaml")
            with open(test_file_path, "w", encoding="utf-8") as file_object:
                file_object.write("---\n")

            with self.assertRaises(RuntimeError):
                runner.ReadTestConfiguration(test_file_path)

        # Test with multiple definitions
        yaml_content = "\n".join(
            [
                "---",
                "name: test1",
                "command: test1",
                "package:",
                "  path: /pkg1",
                "---",
                "name: test2",
                "command: test2",
                "package:",
                "  path: /pkg2",
                "",
            ]
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            test_file_path = os.path.join(temporary_directory, "test.yaml")
            with open(test_file_path, "w", encoding="utf-8") as file_object:
                file_object.write(yaml_content)

            with self.assertRaises(RuntimeError):
                runner.ReadTestConfiguration(test_file_path)

        # Test with empty file
        with tempfile.TemporaryDirectory() as temporary_directory:
            test_file_path = os.path.join(temporary_directory, "test.yaml")
            with open(test_file_path, "w", encoding="utf-8") as file_object:
                _ = file_object

            with self.assertRaises(RuntimeError):
                runner.ReadTestConfiguration(test_file_path)

    @mock.patch("clitooltester.test_runner.subprocess.run")
    @mock.patch("clitooltester.test_runner.shutil.which")
    def testRunTest(self, mock_shutil_which, mock_subprocess_run):
        """Tests the RunTest function."""
        runner = test_runner.TestRunner(quiet=True)

        mock_shutil_which.return_value = "/usr/bin/docker"

        # Test with Docker configuration and subprocess.run success
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        docker = resources.DockerDefinition()
        docker.tag = "test:latest"

        test_definition = resources.TestDefinition()
        test_definition.name = "test"
        test_definition.command = "ls"
        test_definition.docker = docker

        test_result = runner.RunTest(test_definition)
        self.assertEqual(test_result.exit_code, 0)

        # Test with Docker configuration, input and and subprocess.run success
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        docker = resources.DockerDefinition()
        docker.tag = "test:latest"

        test_definition = resources.TestDefinition()
        test_definition.name = "test"
        test_definition.command = "ls %input%"
        test_definition.docker = docker

        test_input = resources.InputDefinition()
        test_input.name = "data"
        test_input.path = "/data/file.bin"

        test_result = runner.RunTest(test_definition, test_input=test_input)
        self.assertEqual(test_result.exit_code, 0)

        # Test with package configuration and subprocess.run success
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"

        test_definition = resources.TestDefinition()
        test_definition.name = "test"
        test_definition.command = "ls"
        test_definition.package = package

        test_result = runner.RunTest(test_definition)
        self.assertEqual(test_result.exit_code, 0)

        # Test with package configuration, input and subprocess.run success
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"

        test_definition = resources.TestDefinition()
        test_definition.name = "test"
        test_definition.command = "ls %input%"
        test_definition.package = package

        test_input = resources.InputDefinition()
        test_input.name = "data"
        test_input.path = "/data/file.bin"

        test_result = runner.RunTest(test_definition, test_input=test_input)
        self.assertEqual(test_result.exit_code, 0)

    @mock.patch("clitooltester.test_runner.subprocess.run")
    def testRunTests(self, mock_subprocess_run):
        """Tests the RunTests function."""
        runner = test_runner.TestRunner(quiet=True)

        # Test single job without input
        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"

        test_definition = resources.TestDefinition()
        test_definition.name = "test"
        test_definition.command = "ls"
        test_definition.package = package

        results = runner.RunTests(test_definition, jobs=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].exit_code, 0)

        # Test single job with input
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"

        test_definition = resources.TestDefinition()
        test_definition.name = "test"
        test_definition.command = "ls %input%"
        test_definition.package = package

        test_input1 = resources.InputDefinition()
        test_input1.name = "input1"
        test_input1.path = "/data/file1.bin"

        test_input2 = resources.InputDefinition()
        test_input2.name = "input2"
        test_input2.path = "/data/file2.bin"

        runner = test_runner.TestRunner(quiet=True)
        results = runner.RunTests(
            test_definition,
            jobs=1,
            test_inputs=[test_input1, test_input2],
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].exit_code, 0)
        self.assertEqual(results[1].exit_code, 0)

        # Test with multiple jobs without input
        mock_subprocess_run.reset_mock()

        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"

        test_definition = resources.TestDefinition()
        test_definition.name = "test"
        test_definition.command = "ls"
        test_definition.package = package

        results = runner.RunTests(test_definition, jobs=2)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].exit_code, 0)

        # Test with multiple jobs with input
        mock_subprocess_run.reset_mock()

        mock_result_success = mock.MagicMock()
        mock_result_success.returncode = 0
        mock_result_success.stdout = ""
        mock_result_success.stderr = ""

        mock_result_failure = mock.MagicMock()
        mock_result_failure.returncode = 1
        mock_result_failure.stdout = ""
        mock_result_failure.stderr = ""

        mock_subprocess_run.side_effect = [
            mock_result_success,
            mock_result_failure,
            mock_result_success,
        ]
        package = resources.PackageDefinition()
        package.path = "/home/user/pkg"

        test_definition = resources.TestDefinition()
        test_definition.name = "test"
        test_definition.command = "ls %input%"
        test_definition.package = package

        test_inputs = []
        for index in range(3):
            test_input = resources.InputDefinition()
            test_input.name = f"input{index:d}"
            test_input.path = f"/data/file{index:d}.bin"
            test_inputs.append(test_input)

        results = runner.RunTests(test_definition, jobs=2, test_inputs=test_inputs)
        self.assertEqual(len(results), 3)

        exit_codes = [result.exit_code for result in results]
        self.assertEqual(exit_codes.count(0), 2)
        self.assertEqual(exit_codes.count(1), 1)


if __name__ == "__main__":
    unittest.main()
