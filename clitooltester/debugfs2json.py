"""Converts debugfs stat output to JSON."""

import fileinput
import json

from datetime import datetime
from typing import Dict
from typing import IO


class Debugfs2Json:
    """Converts debugfs stat output to JSON."""

    SECTION_HEADERS = {
        "BLOCKS:": "blocks",
        "EXTENTS:": "extents",
        "Extended attributes:": "extended_attributes",
    }

    DEFAULT_ATTRIBUTE_NAMES = {
        "atime": "access_time",
        "blockcount": "number_of_blocks",
        "crtime": "creation_time",
        "ctime": "change_time",
        "file acl": "file_acl",
        "flags": "flags",
        "generation": "nfs_generation_number",
        "group": "group_identifier",
        "inode": "inode_number",
        "links": "number_of_links",
        "mtime": "modification_time",
        "project": "project_identifier",
        "size": "size",
        "user": "user_identifier",
        "version": "version",
    }

    # TODO: determine how debugfs represents a socket.
    FILE_TYPES = {
        "block special": 0x6000,
        "character special": 0x2000,
        "directory": 0x4000,
        "FIFO": 0x1000,
        "regular": 0x8000,
        "symlink": 0xA000,
    }

    def _parse_date_time(self, value: str) -> str:
        """Converts a debugfs date and time value to ISO 8601.

        Args:
          value (str): date and time value such as 'Wed Aug 19 18:48:01 2020'

        Returns:
          str: ISO 8601 formatted date and time value.

        Raises:
          RuntimeError: if the date and time value is not supported.
        """
        # TODO: check weekday value[0:3]
        try:
            date_time = datetime.strptime(value[4:], "%b %d %H:%M:%S %Y")
        except ValueError as exception:
            raise RuntimeError(
                f"Unable to parse date and time: {value:s}"
            ) from exception

        return date_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _parse_file_mode(self, file_type: str, permissions: str) -> str:
        """Converts a file mode string to an octal representation.

        Args:
          file_type (str): file type, such as 'directory'.
          permissions (str): octal representation of permissions, such as '0644'.

        Returns:
          str: octal representation of the file mode.
        """
        try:
            numeric_value = int(permissions, 8)
        except ValueError as exception:
            raise RuntimeError(
                "Unable to parse permissions: {permissions:s}"
            ) from exception

        try:
            numeric_value += self.FILE_TYPES.get(file_type)
        except TypeError as exception:
            raise RuntimeError("Unsupported file type: {file_type:s}") from exception

        return f"0o{numeric_value:o}"

    def _parse_section_default(self, line: str, result: Dict[str, str]):
        """Parses a line of the default section.

        Args:
          line (str): line in the section.
          result (dict): resulting attributes.

        Raises:
          RuntimeError: if the line is not supported.
        """
        file_type = "regular"

        if (
            line.startswith("atime:")
            or line.startswith("crtime:")
            or line.startswith("ctime:")
            or line.startswith("mtime:")
        ):
            key, _, value = line.partition(":")
            key = key.lower()

            attribute_name = self.DEFAULT_ATTRIBUTE_NAMES.get(key)
            if " -- " not in value:
                raise RuntimeError(f"Unsupported date and time: {line:s}")

            values = value.strip().split(" -- ")

            result[attribute_name] = self._parse_date_time(values[1])

        elif line.startswith("Fragment:"):
            if line != "Fragment:  Address: 0    Number: 0    Size: 0":
                raise RuntimeError(f"Unsupported fragment: {line:s}")

        elif line.startswith("Size of extra inode fields:"):
            pass

        else:
            while line:
                key, _, line = line.strip().partition(":")
                key = key.lower()

                value, _, line = line.strip().partition(" ")

                if key == "mode":
                    result["file_mode"] = self._parse_file_mode(
                        file_type, value.strip()
                    )
                elif key == "type":
                    file_type = value.strip()

                else:
                    attribute_name = self.DEFAULT_ATTRIBUTE_NAMES.get(key)
                    if not attribute_name:
                        raise RuntimeError(f"Unsupported key: {key:s}")

                    result[attribute_name] = value.strip()

    def convert(self, file_object: IO):
        """Converts debugfs stat output to JSON.

        Args:
          file_object (file): file-like object containing the debugfs stat output.

        Returns:
          dict: dictionary representation of the debugfs stat output.
        """
        result = {}
        section = "default"

        for line in file_object:
            line = line.strip()
            if not line:
                continue

            if line in self.SECTION_HEADERS:
                section = self.SECTION_HEADERS.get(line)

            elif line.startswith("Inode checksum:"):
                result["checksum"] = line[15:].strip()

            elif section == "blocks":
                # TODO: convert block numbers into ranges
                pass

            elif section == "default":
                self._parse_section_default(line, result)

            elif section == "extended_attributes":
                # TODO: parse extended attributes.
                pass

            elif section == "extents":
                # TODO: convert extents into ranges
                pass

        return result


if __name__ == "__main__":
    converter = Debugfs2Json()
    result_dict = converter.convert(fileinput.input())
    json_string = json.dumps(result_dict, indent=2)
    print(json_string)
