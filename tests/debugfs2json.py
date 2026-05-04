"""Tests for the debugfs stat output to JSON converter."""

import unittest

from clitooltester import debugfs2json

from tests import test_lib


class Debugfs2JsonTestCase(test_lib.BaseTestCase):
    """Tests for the debugfs stat output to JSON converter."""

    # TODO: add tests for _parse_date_time
    # TODO: add tests for _parse_file_mode
    # TODO: add tests for _parse_section_default

    def test_convert_with_ext2(self):
        """Tests the convert function with ext2 debugfs stat output."""
        test_file = self._get_test_file_path(["ext2.debugfs"])
        self._skip_if_path_not_exists(test_file)

        with open(test_file, encoding="utf-8") as file_object:
            result = debugfs2json.Debugfs2Json().convert(file_object)

        expected_result = {
            "access_time": "2020-08-19T18:48:01Z",
            "change_time": "2020-08-19T18:48:01Z",
            "file_mode": "0o100664",
            "file_acl": "165",
            "flags": "0x0",
            "group_identifier": "1000",
            "inode_number": "22",
            "modification_time": "2020-08-19T18:48:01Z",
            "nfs_generation_number": "825520578",
            "number_of_blocks": "2",
            "number_of_links": "1",
            "size": "0",
            "user_identifier": "1000",
            "version": "0x00000001",
        }
        self.assertEqual(result, expected_result)

    def test_convert_with_ext4(self):
        """Tests the convert function with ext4 debugfs stat output."""
        test_file = self._get_test_file_path(["ext4.debugfs"])
        self._skip_if_path_not_exists(test_file)

        with open(test_file, encoding="utf-8") as file_object:
            result = debugfs2json.Debugfs2Json().convert(file_object)

        expected_result = {
            "access_time": "2020-08-19T18:48:20Z",
            "change_time": "2020-08-19T18:48:20Z",
            "checksum": "0xaf09bdb6",
            "creation_time": "2020-08-19T18:48:20Z",
            "file_acl": "49",
            "file_mode": "0o100664",
            "flags": "0x80000",
            "group_identifier": "1000",
            "inode_number": "22",
            "modification_time": "2020-08-19T18:48:20Z",
            "nfs_generation_number": "1550207938",
            "number_of_blocks": "2",
            "number_of_links": "1",
            "project_identifier": "0",
            "size": "0",
            "user_identifier": "1000",
            "version": "0x00000000:00000001",
        }
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
