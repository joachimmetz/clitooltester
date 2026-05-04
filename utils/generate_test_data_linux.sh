#!/usr/bin/env bash
#
# Script to generate CLIToolTester test files on Linux.

EXIT_SUCCESS=0;
EXIT_FAILURE=1;

# Checks the availability of a binary and exits if not available.
#
# Arguments:
#   a string containing the name of the binary
#
assert_availability_binary()
{
	local BINARY=$1;

	which ${BINARY} > /dev/null 2>&1;
	if test $? -ne ${EXIT_SUCCESS};
	then
		echo "Missing binary: ${BINARY}";
		echo "";

		exit ${EXIT_FAILURE};
	fi
}

assert_availability_binary debugfs;
assert_availability_binary istat;

set -e;

mkdir -p test_data;

TZ=UTC debugfs -R "stat <22>" ext2.raw > test_data/ext2.debugfs
TZ=UTC debugfs -R "stat <22>" ext4.raw > test_data/ext4.debugfs

TZ=UTC istat ext2.raw 22 > test_data/ext2.istat
TZ=UTC istat ext4.raw 22 > test_data/ext4.istat
