"""YAML-based definitions files."""

import os
import yaml

from clitooltester import resources


class YAMLInputsDefinitionsFile:
    """YAML-based inputs definitions file.

    A YAML-based inputs definitions file contains one or more input definitions. An
    input definition consists of a single input:

    name: ext2
    description: ext2 file system storage media image
    path: test_data/ext2.raw
    parameters:
      partition_offset: 0

    or a set of inputs:

    set:
      name: ext
      description: Extended File System (ext) storage media images
      base_path: test_data
      elements:
        name: ext2
        description: ext2 file system storage media image
        path: ext2.raw
        parameters:
          partition_offset: 0

    Where:
    * description, optional description;
    * name, that uniquely identifies the input;
    * parameters, optional parameters.
    * path, location of the input;
    * set, input set.

    Note that uniqueness of the name is not enforced.
    """

    _SUPPORTED_KEYS = frozenset(["description", "name", "parameters", "path", "set"])

    def _ReadInputDefinition(self, yaml_input_definition):
        """Reads an input definition from a dictionary.

        Args:
          yaml_input_definition (dict[str, object]): YAML input definition values.

        Returns:
          InputDefinition: input definition.

        Raises:
          RuntimeError: if the format of the input definition is not set or incorrect.
        """
        if not yaml_input_definition:
            raise RuntimeError("Missing input definition values.")

        different_keys = set(yaml_input_definition) - self._SUPPORTED_KEYS
        if different_keys:
            different_keys = ", ".join(different_keys)
            raise RuntimeError(f"Undefined keys: {different_keys:s}")

        input_set = yaml_input_definition.get("set")

        if input_set:
            input_definition = self._ReadInputSetDefinition(input_set)
        else:
            name = yaml_input_definition.get("name")
            if not name:
                raise RuntimeError("Invalid input definition missing name.")

            path = yaml_input_definition.get("path")
            if not path:
                raise RuntimeError("Invalid input definition missing path.")

            input_definition = resources.InputDefinition()
            input_definition.description = yaml_input_definition.get("description")
            input_definition.name = name
            input_definition.parameters = yaml_input_definition.get("parameters")
            input_definition.path = path

        return input_definition

    def _ReadInputSetDefinition(self, yaml_input_set_definition):
        """Reads an input set definition from a dictionary.

        Args:
          yaml_input_set_definition (dict[str, object]): YAML input set definition
              values.

        Returns:
          InputSetDefinition: input set definition.

        Raises:
          RuntimeError: if the format of the input set definition is not set or
              incorrect.
        """
        if not yaml_input_set_definition:
            raise RuntimeError("Missing input definition values.")

        name = yaml_input_set_definition.get("name")
        if not name:
            raise RuntimeError("Invalid input set definition missing name.")

        base_path = yaml_input_set_definition.get("base_path")
        if not base_path:
            raise RuntimeError("Invalid input set definition missing base path.")

        elements = yaml_input_set_definition.get("elements")
        if not elements:
            raise RuntimeError("Invalid input set definition missing elements.")

        input_set_definition = resources.InputSetDefinition()
        input_set_definition.base_path = base_path
        input_set_definition.name = name

        for index, element in enumerate(elements):
            name = element.get("name")
            if not name:
                raise RuntimeError(
                    f"Invalid input definition element: {index:d} missing name."
                )

            path = element.get("path")
            if not path:
                raise RuntimeError(
                    f"Invalid input definition element {index:d} with name: {name:s} "
                    f"missing path."
                )

            input_definition = resources.InputDefinition()
            input_definition.description = element.get("description")
            input_definition.name = name
            input_definition.parameters = element.get("parameters")
            input_definition.path = path

            input_set_definition.elements.append(input_definition)

        return input_set_definition

    def _ReadFromFileObject(self, file_object):
        """Reads the input definions from a file-like object.

        Args:
          file_object (file): input definions file-like object.

        Yields:
          InputDefinition: input definition.
        """
        yaml_generator = yaml.safe_load_all(file_object)

        for yaml_input_definition in yaml_generator:
            input_definition = self._ReadInputDefinition(yaml_input_definition)
            if isinstance(input_definition, resources.InputDefinition):
                yield input_definition
            else:
                for element in input_definition.elements:
                    element_definition = resources.InputDefinition()
                    element_definition.name = "/".join(
                        [input_definition.name, element.name]
                    )
                    element_definition.path = os.path.join(
                        input_definition.base_path, element.path
                    )
                    if element.parameters:
                        element_definition.parameters = element.parameters.copy()
                    element_definition.set_name = input_definition.name

                    yield element_definition

    def ReadFromFile(self, path):
        """Reads the input definitions from a YAML file.

        Args:
          path (str): path to a input definitions file.

        Yields:
          InputDefinition: input definition.
        """
        with open(path, encoding="utf-8") as file_object:
            yield from self._ReadFromFileObject(file_object)


class YAMLTestDefinitionFile:
    """YAML-based test definitions file.

    A YAML-based test definitions file contains a test definition, which consists of:

    name: plaso_log2timeline
    description: Run log2timeline.py with input
    command: log2timeline.py %input%
    mount:
    package:
      path: /usr/bin
    stdout:
      normalizer: scripts/normalize.py
      reference_file: expected/output.txt
      reference_writer: scripts/writer.py
      validator: scripts/compare.py

    Where:
    * description, optional description;
    * name, that uniquely identifies the test;
    * command, with arguments, with can consist of placeholder values, such as: %input%.
    * mount, configuration to mount %input%.
    * docker, Docker configuration.
    * package, package configuration.
    * stdout, stdout reference configuration.
    * normalizer, optional path to a normalization script or binary to normalize stdout
        before validation.
    * reference_file, optional path to a file that contains stdout to validate against.
    * reference_writer, path to a script or binary to write stdout to a reference file.
    * validator, path to a script or binary to validate (normalized) stdout.

    Note that uniqueness of the name is not enforced.
    """

    _SUPPORTED_KEYS = frozenset(
        [
            "command",
            "description",
            "docker",
            "mount",
            "name",
            "package",
            "stdout",
        ]
    )

    def _ReadDockerDefinition(self, yaml_docker_definition):
        """Reads a Docker definition from a dictionary.

        Args:
          yaml_docker_definition (dict[str, object]): YAML Docker definition values.

        Returns:
          DockerDefinition: Docker definition.

        Raises:
          RuntimeError: if the format of the Docker definition is not set or incorrect.
        """
        if not yaml_docker_definition:
            raise RuntimeError("Missing Docker definition values.")

        tag = yaml_docker_definition.get("tag")
        if not tag:
            raise RuntimeError("Invalid Docker definition missing tag.")

        docker_definition = resources.DockerDefinition()
        docker_definition.tag = tag
        docker_definition.dockerfile = yaml_docker_definition.get("dockerfile")

        return docker_definition

    def _ReadPackageDefinition(self, yaml_package_definition):
        """Reads a package definition from a dictionary.

        Args:
          yaml_package_definition (dict[str, object]): YAML package definition values.

        Returns:
          PackageDefinition: package definition.

        Raises:
          RuntimeError: if the format of the package definition is not set or incorrect.
        """
        if not yaml_package_definition:
            raise RuntimeError("Missing package definition values.")

        path = yaml_package_definition.get("path")
        if not path:
            raise RuntimeError("Invalid package definition missing path.")

        package_definition = resources.PackageDefinition()
        package_definition.build = yaml_package_definition.get("build")
        package_definition.build_env = yaml_package_definition.get("build_env")
        package_definition.env = yaml_package_definition.get("env")
        package_definition.path = path

        return package_definition

    def _ReadStdoutDefinition(self, yaml_stdout_definition):
        """Reads a stdout definition from a dictionary.

        Args:
          yaml_stdout_definition (dict[str, object]): YAML stdout definition values.

        Returns:
          StdoutDefinition: stdout definition.

        Raises:
          RuntimeError: if the format of the stdout definition is not set or incorrect.
        """
        if not yaml_stdout_definition:
            raise RuntimeError("Missing stdout definition values.")

        stdout_definition = resources.StdoutDefinition()
        stdout_definition.normalizer = yaml_stdout_definition.get("normalizer")
        stdout_definition.reference_file = yaml_stdout_definition.get("reference_file")
        stdout_definition.reference_writer = yaml_stdout_definition.get(
            "reference_writer"
        )
        stdout_definition.validator = yaml_stdout_definition.get("validator")

        return stdout_definition

    def _ReadTestDefinition(self, yaml_test_definition):
        """Reads a test definition from a dictionary.

        Args:
          yaml_test_definition (dict[str, object]): YAML test definition values.

        Returns:
          TestDefinition: test definition.

        Raises:
          RuntimeError: if the format of the test definition is not set or incorrect.
        """
        if not yaml_test_definition:
            raise RuntimeError("Missing test definition values.")

        different_keys = set(yaml_test_definition) - self._SUPPORTED_KEYS
        if different_keys:
            different_keys = ", ".join(different_keys)
            raise RuntimeError(f"Undefined keys: {different_keys:s}")

        command = yaml_test_definition.get("command")
        if not command:
            raise RuntimeError("Invalid test definition missing command.")

        name = yaml_test_definition.get("name")
        if not name:
            raise RuntimeError("Invalid test definition missing name.")

        docker_definition = yaml_test_definition.get("docker")
        package_definition = yaml_test_definition.get("package")
        if docker_definition and package_definition:
            raise RuntimeError("Invalid test definition docker and package both set.")

        test_definition = resources.TestDefinition()
        test_definition.command = command
        test_definition.description = yaml_test_definition.get("description")
        test_definition.mount = "mount" in yaml_test_definition
        test_definition.name = name

        stdout_definition = yaml_test_definition.get("stdout")
        if stdout_definition:
            test_definition.stdout = self._ReadStdoutDefinition(stdout_definition)

        if docker_definition:
            test_definition.docker = self._ReadDockerDefinition(docker_definition)
        if package_definition:
            test_definition.package = self._ReadPackageDefinition(package_definition)

        return test_definition

    def _ReadFromFileObject(self, file_object):
        """Reads the test definition from a file-like object.

        Args:
          file_object (file): test definition file-like object.

        Yields:
          TestDefinition: test definition.
        """
        yaml_generator = yaml.safe_load_all(file_object)

        for yaml_test_definition in yaml_generator:
            yield self._ReadTestDefinition(yaml_test_definition)

    def ReadFromFile(self, path):
        """Reads the test definition from a YAML file.

        Args:
          path (str): path to a test definition file.

        Yields:
          TestDefinition: test definition.
        """
        with open(path, encoding="utf-8") as file_object:
            yield from self._ReadFromFileObject(file_object)
