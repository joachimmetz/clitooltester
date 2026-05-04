"""Converts Sleuthkit istat output to JSON."""

import fileinput
import json

from typing import Dict
from typing import IO


class Istat2Json:
    """Converts istat output to JSON."""

    SECTION_HEADERS = {
        "Direct Blocks:": "direct_blocks",
        "Indirect Blocks:": "indirect_blocks",
        "Inode Times:": "inode_times",
    }

    DEFAULT_ATTRIBUTE_NAMES = {
        "flags": "flags",
        "generation id": "nfs_generation_number",
        "group": "group",
        "inode": "inode_number",
        "mode": "file_mode",
        "num of links": "number_of_links",
        "size": "size",
        "symbolic link to": "link_target",
    }

    INODE_TIMES_ATTRIBUTE_NAMES = {
        "accessed": "access_time",
        "file created": "creation_time",
        "file modified": "modification_time",
        "inode modified": "change_time",
    }

    FILE_MODE_PERMISSIONS = {
        "-": 0,
        "r": 4,
        "w": 2,
        "x": 1,
    }

    FILE_MODE_TYPES = {
        "b": 0x6000,
        "c": 0x2000,
        "d": 0x4000,
        "l": 0xA000,
        "p": 0x1000,
        "r": 0x8000,
        "s": 0xC000,
    }

    def _parse_date_time(self, value: str) -> str:
        """Converts a istat date and time value to ISO 8601.

        Args:
          value (str): date and time value such as '2020-08-19 18:48:01 (UTC)' or
              '2020-08-19 18:48:20.183375487 (UTC)'.

        Returns:
          str: ISO 8601 formatted date and time value.

        Raises:
          RuntimeError: if the date and time value is not supported.
        """
        if len(value) < 25 or not value.endswith(" (UTC)"):
            raise RuntimeError(f"Unsupported non-UTC time value: {value:s}")

        return f"{value[0:10]:s}T{value[11:-6]:s}Z"

    def _parse_file_mode(self, file_mode: str) -> str:
        """Converts a file mode string to an octal representation.

        Args:
          file_mode (str): string representatio of the file mode, such as 'rrw-r--r--'
              or 'drwxr-xr-x'.

        Returns:
          str: octal representation of the file mode.
        """
        numeric_value = 0
        for index, character in enumerate(file_mode[-9:]):
            if index in (3, 6):
                numeric_value *= 8

            numeric_value += self.FILE_MODE_PERMISSIONS.get(character)

        numeric_value += self.FILE_MODE_TYPES.get(file_mode[-10])
        return f"0o{numeric_value:o}"

    def _parse_section_default(self, line: str, result: Dict[str, str]):
        """Parses a line of the default section.

        Args:
          line (str): line in the section.
          result (dict): resulting attributes.

        Raises:
          RuntimeError: if the line is not supported.
        """
        if line == "Allocated":
            result["allocated"] = True

        elif line == "Not Allocated":
            result["allocated"] = False

        elif ":" in line:
            key, _, value = line.partition(":")
            key = key.lower()

            if key == "uid / gid":
                values = value.strip().split("/")

                result["user_identifier"] = values[0].strip()
                result["group_identifier"] = values[1].strip()
            else:
                attribute_name = self.DEFAULT_ATTRIBUTE_NAMES.get(key)
                attribute_value = value.strip()

                if attribute_name == "file_mode":
                    attribute_value = self._parse_file_mode(attribute_value)

                result[attribute_name] = attribute_value

        else:
            raise RuntimeError(f"Unsupported line: {line:s}")

    def _parse_section_inode_times(self, line: str, result: Dict[str, str]):
        """Parses a line of the inode times section.

        Args:
          line (str): line in the section.
          result (dict): resulting attributes.

        Raises:
          RuntimeError: if the line is not supported.
        """
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.lower()

            attribute_name = self.INODE_TIMES_ATTRIBUTE_NAMES.get(key)
            attribute_value = value.strip()

            if attribute_name in (
                "access_time",
                "change_time",
                "creation_time",
                "modification_time",
            ):
                attribute_value = self._parse_date_time(attribute_value)

            result[attribute_name] = attribute_value

        else:
            raise RuntimeError(f"Unsupported line: {line:s}")

    def convert(self, file_object: IO):
        """Converts istat output to JSON.

        Args:
          file_object (file): file-like object containing the istat output.

        Returns:
          str: JSON string representation of the istat output.
        """
        result = {}
        section = "default"

        for line in file_object:
            line = line.strip()
            if not line:
                continue

            if line in self.SECTION_HEADERS:
                section = self.SECTION_HEADERS.get(line)
                continue

            if line.startswith("Extended Attributes"):
                section = "extended_attributes"
                continue

            if section == "default":
                self._parse_section_default(line, result)

            elif section == "direct_blocks":
                # TODO: convert direct block numbers into ranges
                pass

            elif section == "extended_attributes":
                # TODO: parse extended attributes.
                pass

            elif section == "indirect_blocks":
                # TODO: convert indirect block numbers into ranges
                pass

            elif section == "inode_times":
                self._parse_section_inode_times(line, result)

        return result


if __name__ == "__main__":
    converter = Istat2Json()
    result_dict = converter.convert(fileinput.input())
    json_string = json.dumps(result_dict, indent=2)
    print(json_string)
