"""Resources."""


class DockerDefinition:
    """Docker definition.

    Attributes:
      command (str): command to run inside the Docker container.
      dockerfile (str): path to a Dockerfile for building the Docker image.
      tag (str): Docker image tag.
    """

    def __init__(self):
        """Initializes a Docker definition."""
        super().__init__()
        self.command = None
        self.dockerfile = None
        self.tag = None


class InputDefinition:
    """Input definition.

    Attributes:
      description (str): description of the input.
      name (str): name that uniquely identifies the input.
      paramters (dict[str, str]): parameters accompanying the input.
      path (str): location of the input.
      set_name (str): name of set the input is part of.
    """

    def __init__(self):
        """Initializes an input definition."""
        super().__init__()
        self.description = None
        self.name = None
        self.parameters = {}
        self.path = None
        self.set_name = None


class InputSetDefinition:
    """Input set definition.

    Attributes:
      base_path (str): base location of the input set, where the location (or path)
          of the elements are relative to the base location.
      elements (list[InputDefinition]): elements in the input set.
      name (str): name that uniquely identifies the input set.
    """

    def __init__(self):
        """Initializes an input set definition."""
        super().__init__()
        self.base_path = None
        self.elements = []
        self.name = None


class PackageDefinition:
    """Package definition.

    Attributes:
      build (str): command(s) to build the package.
      build_env (dict[str, str]): build environment variables.
      env (dict[str, str]): environment variables.
      path (str): location of the package.
    """

    def __init__(self):
        """Initializes a package definition."""
        super().__init__()
        self.build = None
        self.build_env = None
        self.env = None
        self.path = None


class StdoutDefinition:
    """Stdout definition.

    Attributes:
      normalizer (str): path to a normalization script or binary to normalize stdout
          before validation. The normalizer should read stdin and output to stdout.
      reference_file (str): path to a file that contains (canonicalized) stdout to
          validate against.
      reference_writer (str): path to a script or binary to write (normalized) stdout
          to a reference file. The writer should read stdin and output to a file.
      validator (str): path to a script or binary to validate (normalized) stdout. The
          validator should read stdin and take a reference file as argument. The output
          of the validator should be JSON.
    """

    def __init__(self):
        """Initializes a stdout definition."""
        super().__init__()
        self.normalizer = None
        self.reference_file = None
        self.reference_writer = None
        self.validator = None


class TestDefinition:
    """Test definition.

    Commands support placeholder arguments like %input%.

    Attributes:
      command (str): command with arguments.
      docker (DockerDefinition): Optional Docker configuration.
      mount (bool): Value to indicate the input should be mounted before running the
          test command.
      name (str): name that uniquely identifies the test.
      package (PackageDefinition): package definition.
      stdout (StdoutDefinition): stdout reference definition.
    """

    def __init__(self):
        """Initializes a test definition."""
        super().__init__()
        self.command = None
        self.docker = None
        self.mount = False
        self.name = None
        self.package = None
        self.stdout = None


class TestResult:
    """Test result.

    Attributes:
      description (str): description.
      end_time (int): test end time in nanoseconds.
      exit_code (int): exit code from the test command.
      sequence_number (int): sequence number.
      start_time (int): test start time in nanoseconds.
      stderr (str): standard error from the test command.
      stdout (str): standard output from the test command.
      success (bool): True if the test was successful.
    """

    def __init__(self):
        """Initializes a test result."""
        super().__init__()
        self.description = None
        self.end_time = 0
        self.exit_code = 0
        self.sequence_number = 0
        self.start_time = 0
        self.stderr = None
        self.stdout = None
        self.success = None
