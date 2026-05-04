#!/bin/bash

EXIT_SUCCESS=0

FEDORA_VERSIONS=(
	"40"
	"44"
)

SLEUTHKIT_VERSIONS=(
	"4.15.0"
	"4.14.0"
	"4.13.0"
	"4.12.1" "4.12.0"
	"4.11.1" "4.11.0"
	"4.10.2" "4.10.1" "4.10.0"
	"4.9.0"
	"4.8.0"
	"4.7.0"
	"4.6.7" "4.6.6" "4.6.5" "4.6.4" "4.6.3" "4.6.2" "4.6.1" "4.6.0"
	"4.5.0"
	"4.4.2" "4.4.1" "4.4.0"
	"4.3.1" "4.3.0"
	"4.2.0"
	"4.1.3" "4.1.2" "4.1.1" "4.1.0"
	"4.0.2" "4.0.1" "4.0.0"
	"3.2.3" "3.2.2" "3.2.1" "3.2.0"
	"3.1.3" "3.1.2" "3.1.1" "3.1.0"
	"3.0.1" "3.0.0"
)

SLEUTHKIT_VERSIONS=(
	"4.15.0"
	"4.14.0"
	"4.13.0"
	"4.12.0"
)

BUILDS=()

BASE_CONFIG="fedora-base.Dockerfile"
BUILD_CONFIG="fedora-build.Dockerfile"

for FEDORA_VERSION in ${FEDORA_VERSIONS[@]}
do
	BASE_IMAGE="clitooltester/fedora${FEDORA_VERSION}-sleuthkit"

	# Create the base Docker image with necessary build tools.
	docker build \
		--build-arg FEDORA_VERSION="${FEDORA_VERSION}" \
		-f ${BASE_CONFIG} \
		--force-rm \
		--no-cache \
		-t ${BASE_IMAGE} \
		.

	if test $? -ne ${EXIT_SUCCESS}
	then
		continue
	fi

	for SLEUTHKIT_VERSION in ${SLEUTHKIT_VERSIONS[@]}
	do
		BUILD_IMAGE="clitooltester/fedora${FEDORA_VERSION}-sleuthkit-${SLEUTHKIT_VERSION}"

		# Create a version specific Docker image.
		docker build \
			--build-arg FEDORA_VERSION="${FEDORA_VERSION}" \
			--build-arg GIT_TAG="sleuthkit-${SLEUTHKIT_VERSION}" \
			-f ${BUILD_CONFIG} \
			-t ${BUILD_IMAGE} .

		if test $? -ne ${EXIT_SUCCESS}
		then
			continue
		fi
		docker run \
			-u ${UID}:${GID} \
			${BUILD_IMAGE} \
			/bin/bash -c "cd sleuthkit && ./tools/fstools/fls -V"

		if test $? -eq ${EXIT_SUCCESS}
		then
			BUILDS+=("fedora${FEDORA_VERSION}-sleuthkit-${SLEUTHKIT_VERSION}")
		fi
	done
done
