"""Command line tool test runner."""

import os
import pathlib
import plistlib
import re
import shlex
import shutil
import subprocess
import sys
import time

from concurrent import futures

from clitooltester import resources
from clitooltester import yaml_definitions_file


class TestRunner:
    """Command line tool test runner."""

    _PLACEHOLDER_RE = re.compile(r"%[0-9A-Za-z_]+%")

    def __init__(self, quiet=False, verbose=False, write_references=False):
        """Initializes a command line tool test runner.

        Args:
          quiet (Optional[bool]): value to indicate all prints should be disabled,
              overrides verbose.
          verbose (Optional[bool]): value to indicate stdout and stderr should be
              printed on error.
          write_references (Optional[bool]): value to indicate to write reference files.
        """
        super().__init__()
        self._is_posix = os.name == "posix"
        # TODO: allow to set mount point in configuration
        self._mount_point = "/mnt/clitooltester"
        self._quiet = quiet
        self._verbose = verbose
        self._write_references = write_references

    def _MountInput(self, path):
        """Mounts test input.

        Args:
          path (str): path of the test input.

        Raises:
          RuntimeError: if the sudo or mount binary does not exist or the test input
              could not be mounted.
        """
        # TODO: add support for "Mount-VHD -Path %input%"

        arguments = []

        hdiutil_path = shutil.which("hdiutil")
        if hdiutil_path:
            arguments = [
                hdiutil_path,
                "attach",
                "-nobrowse",
                "-readonly",
                "-mountroot",
                self._mount_point,
                path,
            ]
        else:
            sudo_path = shutil.which("sudo")
            if not sudo_path:
                raise RuntimeError("Unable to determine location of sudo binary")

            mount_path = shutil.which("mount")
            if not mount_path:
                raise RuntimeError("Unable to determine location of mount binary")

            arguments = [
                sudo_path,
                mount_path,
                "-o",
                "ro,loop",
                path,
                self._mount_point,
            ]

        if not arguments:
            raise RuntimeError("Unable to determine how to mount input")

        result = subprocess.run(
            arguments,
            capture_output=True,
            check=False,
            shell=False,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Unable to mount input with error: {result.stderr:s}")

    def _NormalizeStdout(self, normalizer, stdout):
        """Normalizes stdout.

        Args:
          normalizer (str): path to the normalization script or binary.
          stdout (str): stdout to normalize.

        Returns:
          CompletedProcess: normalizer process object.

        Raises:
          RuntimeError: if normalizer script or binary does not exist.
        """
        arguments = shlex.split(normalizer, posix=self._is_posix)

        if not os.path.isfile(arguments[0]):
            raise RuntimeError(f"Missing normalizer: {normalizer:s}")

        if arguments[0].endswith(".py"):
            arguments.insert(0, sys.executable)

        return subprocess.run(
            arguments,
            capture_output=True,
            check=False,
            input=stdout,
            shell=False,
            text=True,
        )

    def _PrintTestResult(self, test_result):
        """Prints a test result.

        Args:
          test_result (TestResult): test result.
        """
        if self._quiet:
            return

        print(test_result.description, end="")

        padding_length = max(1, 72 - len(test_result.description))
        print(" " * padding_length, end="")

        if test_result.success:
            print("\033[32mok\033[0m")
        else:
            print("\033[31mFAILED\033[0m")

            if self._verbose and test_result.stdout:
                print(test_result.stdout)
            if self._verbose and test_result.stderr:
                print(test_result.stderr)

    def _ProcessStdout(self, test_definition, test_result, test_input=None):
        """Processes stdout.

        * Normalizes stdout if specified;
        * Compares against reference_file using validator if specified.

        Args:
          test_definition (TestDefinition): test definition with Docker configuration.
          test_result (TestResult): test result to process.
          test_input (Optional[InputDefinition]): input definition.

        Returns:
          bool: True if stdout was processed successfully.

        Raises:
          RuntimeError: if stdout definition is missing.
        """
        if not test_definition.stdout:
            raise RuntimeError("Missing stdout definition")

        stdout_definition = test_definition.stdout
        stdout = test_result.stdout

        test_parameters = {}
        if test_input:
            test_parameters.update(
                {
                    f"%{key:s}%": str(value)
                    for key, value in test_input.parameters.items()
                }
            )
            test_parameters["%input%"] = test_input.name

        if stdout_definition.normalizer and stdout:
            normalizer_process = self._NormalizeStdout(
                stdout_definition.normalizer, stdout
            )
            if normalizer_process.returncode != 0:
                test_result.exit_code = normalizer_process.returncode
                test_result.stderr = normalizer_process.stderr
                test_result.stdout = normalizer_process.stdout
                test_result.success = False
                return

            stdout = normalizer_process.stdout

        reference_file = None
        if stdout_definition.reference_file:
            reference_file = self._SubstitutePlaceholders(
                stdout_definition.reference_file, test_parameters
            )

        if self._write_references and reference_file and stdout:
            if not self._WriteReferenceFile(
                stdout_definition.reference_writer, reference_file, stdout
            ):
                test_result.success = False
                return

        elif stdout_definition.validator and reference_file and stdout:
            validator_process = self._ValidateStdout(
                stdout_definition.validator,
                reference_file,
                stdout,
            )
            if validator_process.returncode != 0:
                test_result.exit_code = validator_process.returncode
                test_result.stderr = validator_process.stderr
                test_result.stdout = validator_process.stdout
                test_result.success = False
                return

            # TODO: parse JSON validation and update test_result

    def _RunTestWithDocker(self, test_definition, test_input=None):
        """Runs a test with Docker.

        Args:
          test_definition (TestDefinition): test definition with Docker configuration.
          test_input (Optional[InputDefinition]): input definition.

        Returns:
          TestResult: test result.

        Raises:
          RuntimeError: if unable to find docker binary or if the command contains
              unresolved placeholders.
          ValueError: if the Docker configuration is missing.
        """
        if not test_definition.docker:
            raise ValueError("Invalid test definition - missing Docker configuration")

        docker_path = shutil.which("docker")
        if not docker_path:
            raise RuntimeError("Unable to determine location of docker binary")

        arguments = [docker_path, "run", "--rm", "--security-opt", "label=disable"]
        test_description = f"{test_definition.name:s}"
        test_parameters = {}
        path_mounted = None

        if test_input:
            path = pathlib.Path(test_input.path)
            if not path.is_absolute():
                path = path.resolve()

            if test_definition.mount:
                path_mounted = str(path)
                self._MountInput(path_mounted)
                volume_path = self._mount_point
            else:
                volume_path = f"{path.parent!s}"

            arguments.extend(["-v", f"{volume_path:s}:/input:ro"])
            test_description = f"{test_description:s} with input: '{test_input.name:s}'"
            test_parameters.update(
                {
                    f"%{key:s}%": str(value)
                    for key, value in test_input.parameters.items()
                }
            )
            if test_definition.mount:
                test_parameters["%mountpoint%"] = "/input"
            else:
                test_parameters["%input%"] = f'"/input/{path.name:s}"'

        docker_definition = test_definition.docker

        arguments.append(docker_definition.tag)

        command = self._SubstitutePlaceholders(test_definition.command, test_parameters)

        matches = self._PLACEHOLDER_RE.findall(command)
        if matches:
            placeholders = ", ".join(matches)
            raise RuntimeError(
                f"Command contains unresolved placeholders: {placeholders:s}"
            )

        arguments.extend(shlex.split(command, posix=self._is_posix))

        test_result = resources.TestResult()
        test_result.start_time = time.time_ns()

        subprocess_result = subprocess.run(
            arguments,
            capture_output=True,
            check=False,
            shell=False,
            text=True,
        )
        test_result.description = test_description
        test_result.end_time = time.time_ns()
        test_result.exit_code = subprocess_result.returncode
        test_result.stderr = subprocess_result.stderr
        test_result.stdout = subprocess_result.stdout
        test_result.success = subprocess_result.returncode == 0

        if path_mounted:
            self._UnmountInput(path_mounted)

        if test_definition.stdout:
            self._ProcessStdout(test_definition, test_result, test_input=test_input)

        return test_result

    def _RunTestWithPackage(self, test_definition, test_input=None):
        """Runs a test.

        Args:
          test_definition (TestDefinition): test definition with Docker configuration.
          test_input (Optional[InputDefinition]): input definition.

        Returns:
          TestResult: test result.

        Raises:
          RuntimeError: if the command contains unresolved placeholders.
          ValueError: if the package configuration is missing.
        """
        test_description = f"{test_definition.name:s}"
        test_parameters = {}
        path_mounted = None

        package_path = getattr(test_definition.package, "path", None)
        if package_path:
            test_parameters["%package%"] = f'"{package_path:s}"'

        if test_input:
            test_description = f"{test_description:s} with input: '{test_input.name:s}'"
            test_parameters.update(
                {
                    f"%{key:s}%": str(value)
                    for key, value in test_input.parameters.items()
                }
            )
            if test_definition.mount:
                path_mounted = test_input.path
                self._MountInput(path_mounted)

                test_parameters["%mountpoint%"] = self._mount_point
            else:
                test_parameters["%input%"] = f'"{test_input.path:s}"'

        command = self._SubstitutePlaceholders(test_definition.command, test_parameters)

        matches = self._PLACEHOLDER_RE.findall(command)
        if matches:
            placeholders = ", ".join(matches)
            raise RuntimeError(
                f"Command contains unresolved placeholders: {placeholders:s}"
            )

        arguments = shlex.split(command, posix=self._is_posix)

        test_result = resources.TestResult()
        test_result.start_time = time.time_ns()
        test_env = getattr(test_definition.package, "env", None)

        subprocess_result = subprocess.run(
            arguments,
            capture_output=True,
            check=False,
            env=test_env,
            shell=False,
            text=True,
        )
        test_result.description = test_description
        test_result.end_time = time.time_ns()
        test_result.exit_code = subprocess_result.returncode
        test_result.stderr = subprocess_result.stderr
        test_result.stdout = subprocess_result.stdout
        test_result.success = subprocess_result.returncode == 0

        if path_mounted:
            self._UnmountInput(path_mounted)

        if test_definition.stdout:
            self._ProcessStdout(test_definition, test_result, test_input=test_input)

        return test_result

    def _SubstitutePlaceholders(self, command, test_parameters):
        """Substitutes placeholders in a command.

        Supported placeholders:
          "%input%", which represents the path of the input.
          "%package%", which represents the path of the package.

        Args:
          command (str): command with placeholders.
          test_parameters (dict[str, str]): test parameters.

        Returns:
          str: command with placeholders substituted.
        """
        for key, value in test_parameters.items():
            command = command.replace(key, value)

        return command

    def _UnmountInput(self, path):
        """Unmounts test input.

        Args:
          path (str): path of the test input.

        Raises:
          RuntimeError: if the sudo or umount binary does not exist or the test input
              could not be unmounted.
        """
        # TODO: add support for "Dismount-VHD -Path %input%"

        hdiutil_path = shutil.which("hdiutil")
        if hdiutil_path:
            result = subprocess.run(
                [hdiutil_path, "info", "-plist"],
                capture_output=True,
                check=True,
                shell=False,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Unable to run: 'hdiutil info -plist' with error: "
                    f"{result.stderr:s}"
                )

            try:
                hdiutil_info = plistlib.loads(result.stdout)
            except Exception as exception:
                raise RuntimeError(
                    "Unable to parse output of: 'hdiutil info -plist'"
                ) from exception

            path = os.path.abspath(path)
            volume_paths = []
            for image in hdiutil_info.get("images") or []:
                image_path = image.get("image-path")
                if not image_path:
                    continue

                image_path = os.path.abspath(image_path)
                if path != image_path:
                    continue

                for system_entity in image.get("system-entities") or []:
                    mount_point = system_entity.get("mount-point")
                    if mount_point:
                        volume_paths.append(mount_point)

            result = True
            for volume_path in volume_paths:
                arguments = [hdiutil_path, "detach", volume_path]

                try:
                    subprocess.run(
                        arguments,
                        capture_output=True,
                        check=True,
                        shell=False,
                        text=True,
                    )
                except subprocess.CalledProcessError:
                    result = False

            if not result:
                raise RuntimeError("Unable to umount input")

        else:
            sudo_path = shutil.which("sudo")
            if not sudo_path:
                raise RuntimeError("Unable to determine location of sudo binary")

            umount_path = shutil.which("umount")
            if not umount_path:
                raise RuntimeError("Unable to determine location of umount binary")

            arguments = [sudo_path, umount_path, self._mount_point]

            try:
                subprocess.run(
                    arguments,
                    capture_output=True,
                    check=True,
                    shell=False,
                    text=True,
                )
            except subprocess.CalledProcessError as exception:
                raise RuntimeError("Unable to umount input") from exception

    def _WriteReferenceFile(
        self,
        reference_writer,
        reference_file,
        stdout,
    ):
        """Writes stdout to a reference file.

        Args:
          reference_writer (str): path to the reference file writer script or binary.
          reference_file (str): path to the reference file.
          stdout (str): the stdout to compare.

        Returns:
          bool: True if the file was successfully written.
        """
        reference_directory = os.path.dirname(os.path.abspath(reference_file))
        os.makedirs(reference_directory, exist_ok=True)

        if reference_writer:
            if reference_writer.endswith(".py"):
                arguments = [sys.executable, reference_writer, reference_file]
            else:
                arguments = [reference_writer, reference_file]

            result = subprocess.run(
                arguments,
                capture_output=True,
                check=False,
                input=stdout,
                shell=False,
                text=True,
            )
            if result.returncode != 0:
                return False

        else:
            with open(reference_file, "w", encoding="utf-8") as file_object:
                file_object.write(stdout)

        return True

    def _ValidateStdout(
        self,
        validator,
        reference_file,
        stdout,
    ):
        """Validates stdout against a reference file.

        Args:
          validator (str): path to the validation script or binary.
          reference_file (str): path to the reference file.
          stdout (str): the stdout to compare.

        Returns:
          CompletedProcess: validator process object.

        Raises:
          RuntimeError: if validator script or binary, or reference file does not
              exist.
        """
        arguments = shlex.split(validator, posix=self._is_posix)

        if not os.path.isfile(arguments[0]):
            raise RuntimeError(f"Missing validator: {validator:s}")

        if arguments[0].endswith(".py"):
            arguments.insert(0, sys.executable)

        if not os.path.isfile(reference_file):
            raise RuntimeError(f"Missing reference file: {reference_file:s}")

        arguments.append(reference_file)

        return subprocess.run(
            arguments,
            capture_output=True,
            check=False,
            input=stdout,
            shell=False,
            text=True,
        )

    def BuildPackage(self, test_definition):
        """Builds a package before running tests.

        Args:
          test_definition (TestDefinition): test definition with Docker configuration.

        Returns:
          int: exit code from the build command.

        Raises:
          RuntimeError: if the command contains unresolved placeholders.
          ValueError: if the package configuration is missing.
        """
        if not test_definition.package:
            raise ValueError("Invalid test definition - missing package configuration")

        # Note that the user shell is used to not to have to set up the build
        # environment.
        shell = os.environ.get("SHELL", "/bin/bash")

        arguments = [shell, "-l", "-i", "-c"]
        test_parameters = {"%package%": f'"{test_definition.package.path:s}"'}

        command = self._SubstitutePlaceholders(
            test_definition.package.build, test_parameters
        )
        matches = self._PLACEHOLDER_RE.findall(command)
        if matches:
            placeholders = ", ".join(matches)
            raise RuntimeError(
                f"Command contains unresolved placeholders: {placeholders:s}"
            )

        arguments.extend(shlex.split(command, posix=self._is_posix))

        result = subprocess.run(
            arguments,
            capture_output=True,
            check=False,
            cwd=test_definition.package.path,
            env=test_definition.package.build_env,
            shell=False,
            text=True,
        )
        if not self._quiet and result.returncode != 0:
            if self._verbose and result.stdout:
                print(result.stdout)
            if self._verbose and result.stderr:
                print(result.stderr)

        return result.returncode

    def BuildDockerImage(self, test_definition):
        """Builds a Docker image from a Dockerfile.

        Args:
          test_definition (TestDefinition): test definition with Docker configuration.

        Returns:
          int: exit code from the build command.

        Raises:
          RuntimeError: if unable to find docker binary.
          ValueError: if the Docker configuration is missing.
        """
        if not test_definition.docker:
            raise ValueError("Invalid test definition - missing Docker configuration")

        if not test_definition.docker.dockerfile:
            raise ValueError("Invalid Docker definition - missing dockerfile")

        docker_path = shutil.which("docker")
        if not docker_path:
            raise RuntimeError("Unable to determine location of docker binary")

        arguments = [
            docker_path,
            "build",
            "-t",
            test_definition.docker.tag,
            "-f",
            test_definition.docker.dockerfile,
            ".",
        ]
        result = subprocess.run(
            arguments,
            capture_output=True,
            check=False,
            shell=False,
            text=True,
        )
        if not self._quiet and result.returncode != 0:
            if self._verbose and result.stdout:
                print(result.stdout)
            if self._verbose and result.stderr:
                print(result.stderr)

        return result.returncode

    def ReadInputsConfiguration(self, path):
        """Reads the inputs configuration from a file.

        Args:
          path (str): path of the configuration file.

        Returns:
          list[InputDefinitions]: input definitions.
        """
        yaml_definition_file = yaml_definitions_file.YAMLInputsDefinitionsFile()

        return list(yaml_definition_file.ReadFromFile(path))

    def ReadTestConfiguration(self, path):
        """Reads the test configuration from a file.

        Args:
          path (str): path of the configuration file.

        Returns:
          TestDefinition: test definition.

        Raises:
          RuntimeError: if test definition is missing.
        """
        yaml_definition_file = yaml_definitions_file.YAMLTestDefinitionFile()

        test_definitions = list(yaml_definition_file.ReadFromFile(path))
        if not test_definitions:
            raise RuntimeError("Missing test definitions")

        if len(test_definitions) != 1:
            raise RuntimeError("More than 1 test definition currently not supported")

        return test_definitions[0]

    def RunTest(self, test_definition, test_input=None):
        """Runs a test.

        Args:
          test_definition (TestDefinition): test definition with Docker configuration.
          test_input (Optional[InputDefinition]): input definition.

        Returns:
          TestResult: test result.
        """
        if test_definition.docker:
            return self._RunTestWithDocker(test_definition, test_input=test_input)

        return self._RunTestWithPackage(test_definition, test_input=test_input)

    def RunTests(self, test_definition, jobs=1, test_inputs=None):
        """Runs tests and collects results.

        Args:
          test_definition (TestDefinition): test definition.
          jobs (Optional[int]): number of parallel jobs to run, where 1 is sequential.
          test_inputs (Optional[list[InputDefinition]]): input definitions.

        Returns:
          list[int]: list of exit codes from each test.

        Raises:
          RuntimeError: if the test configuration is not supported.
        """
        if test_definition.mount:
            if jobs > 1:
                raise RuntimeError("parallel jobs with mount currently not supported")

            if not os.path.isdir(self._mount_point):
                raise RuntimeError(f"Missing mount point: '{self._mount_point:s}'")

        if test_inputs:
            tasks = [(test_definition, test_input) for test_input in test_inputs]
        else:
            tasks = [(test_definition, None)]

        results = [None] * len(tasks)

        def _run_job(task_index, task):
            test_runner = TestRunner(
                quiet=self._quiet,
                verbose=self._verbose,
                write_references=self._write_references,
            )
            test_run = test_runner.RunTest(*task)
            test_run.sequence_number = task_index
            return test_run

        if jobs <= 1:
            for task_index, task in enumerate(tasks):
                test_result = _run_job(task_index, task)

                results[test_result.sequence_number] = test_result

                self._PrintTestResult(test_result)
        else:
            with futures.ThreadPoolExecutor(max_workers=jobs) as executor:
                future_instances = {
                    executor.submit(_run_job, task_index, task): (task_index, task)
                    for task_index, task in enumerate(tasks)
                }
                for future in futures.as_completed(future_instances):
                    test_result = future.result()

                    results[test_result.sequence_number] = test_result

                    self._PrintTestResult(test_result)

        return results
