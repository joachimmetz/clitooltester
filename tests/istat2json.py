"""Tests for the SleuthKit istat output to JSON converter."""

import unittest

from clitooltester import istat2json

from tests import test_lib


class Istat2JsonTestCase(test_lib.BaseTestCase):
    """Tests for the istat output to JSON converter."""

    # pylint: disable=protected-access

    # TODO: add tests for _parse_date_time

    def test_parse_file_mode(self):
        """Tests the _parse_file_mode function."""
        converter = istat2json.Istat2Json()

        result = converter._parse_file_mode("brw-rw-r--")
        self.assertEqual(result, "0o60664")

        result = converter._parse_file_mode("crw-rw-rw-")
        self.assertEqual(result, "0o20666")

        result = converter._parse_file_mode("drwxr-xr-x")
        self.assertEqual(result, "0o40755")

        result = converter._parse_file_mode("lrwxrwxrwx")
        self.assertEqual(result, "0o120777")

        result = converter._parse_file_mode("prw-r--r--")
        self.assertEqual(result, "0o10644")

        result = converter._parse_file_mode("rrw-r--r--")
        self.assertEqual(result, "0o100644")

        result = converter._parse_file_mode("srwxrwxrwx")
        self.assertEqual(result, "0o140777")

    def test_parse_section_default(self):
        """Tests the _parse_section_default function."""
        converter = istat2json.Istat2Json()

        result = {}
        converter._parse_section_default("Allocated", result)
        self.assertEqual(result, {"allocated": True})

        result = {}
        converter._parse_section_default("Not Allocated", result)
        self.assertEqual(result, {"allocated": False})

        result = {}
        converter._parse_section_default("uid / gid: 1000 / 1000", result)
        self.assertEqual(
            result, {"user_identifier": "1000", "group_identifier": "1000"}
        )

        result = {}
        converter._parse_section_default("inode: 22", result)
        self.assertEqual(result, {"inode_number": "22"})

        result = {}
        converter._parse_section_default("mode: rrw-r--r--", result)
        self.assertEqual(result, {"file_mode": "0o100644"})

        with self.assertRaises(RuntimeError):
            result = {}
            converter._parse_section_default("Bogus", result)

    def test_parse_section_inode_times(self):
        """Tests the _parse_section_default function."""
        converter = istat2json.Istat2Json()

        result = {}
        converter._parse_section_inode_times(
            "Accessed: 2020-08-19 18:48:16 (UTC)", result
        )
        expected_result = {"access_time": "2020-08-19T18:48:16Z"}
        self.assertEqual(result, expected_result)

        result = {}
        converter._parse_section_inode_times(
            "File Modified: 2020-08-19 18:48:16 (UTC)", result
        )
        expected_result = {"modification_time": "2020-08-19T18:48:16Z"}
        self.assertEqual(result, expected_result)

        result = {}
        converter._parse_section_inode_times(
            "Inode Modified: 2020-08-19 18:48:16 (UTC)", result
        )
        expected_result = {"change_time": "2020-08-19T18:48:16Z"}
        self.assertEqual(result, expected_result)

        result = {}
        converter._parse_section_inode_times(
            "File Created: 2020-08-19 18:48:16.123456789 (UTC)", result
        )
        expected_result = {"creation_time": "2020-08-19T18:48:16.123456789Z"}
        self.assertEqual(result, expected_result)

        with self.assertRaises(RuntimeError):
            result = {}
            converter._parse_section_inode_times(
                "Accessed: 2020-08-19 18:48:16 PST", result
            )

        with self.assertRaises(RuntimeError):
            result = {}
            converter._parse_section_inode_times("Bogus", result)

    def test_convert_with_ext2(self):
        """Tests the convert function with ext2 istat output."""
        test_file = self._get_test_file_path(["ext2.istat"])
        self._skip_if_path_not_exists(test_file)

        with open(test_file, encoding="utf-8") as file_object:
            result = istat2json.Istat2Json().convert(file_object)

        expected_result = {
            "access_time": "2020-08-19T18:48:01Z",
            "allocated": True,
            "change_time": "2020-08-19T18:48:01Z",
            "file_mode": "0o100664",
            "group": "0",
            "group_identifier": "1000",
            "inode_number": "22",
            "modification_time": "2020-08-19T18:48:01Z",
            "nfs_generation_number": "825520578",
            "number_of_links": "1",
            "size": "0",
            "user_identifier": "1000",
        }
        self.assertEqual(result, expected_result)

    def test_convert_with_ext4(self):
        """Tests the convert function with ext4 istat output."""
        test_file = self._get_test_file_path(["ext4.istat"])
        self._skip_if_path_not_exists(test_file)

        with open(test_file, encoding="utf-8") as file_object:
            result = istat2json.Istat2Json().convert(file_object)

        expected_result = {
            "access_time": "2020-08-19T18:48:20.183375487Z",
            "allocated": True,
            "change_time": "2020-08-19T18:48:20.184375489Z",
            "creation_time": "2020-08-19T18:48:20.183375487Z",
            "file_mode": "0o100664",
            "flags": "Extents,",
            "group": "0",
            "group_identifier": "1000",
            "inode_number": "22",
            "modification_time": "2020-08-19T18:48:20.183375487Z",
            "nfs_generation_number": "1550207938",
            "number_of_links": "1",
            "size": "0",
            "user_identifier": "1000",
        }
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
