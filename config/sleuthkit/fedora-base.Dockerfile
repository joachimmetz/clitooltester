ARG FEDORA_VERSION=44

FROM fedora:${FEDORA_VERSION}

# Create container with:
# docker build -f fedora-sleuthkit-base.Dockerfile --force-rm --no-cache -t clitooltester/fedora44-sleuthkit .

ARG UID=1000
ARG GID=1000

RUN dnf install -y \
	@development-tools \
	autoconf \
	automake \
	dnf-plugins-core \
	gcc-c++ \
	git \
	libtool \
	pkg-config

RUN groupadd --gid ${GID} build && \
    useradd --create-home --gid ${GID} --shell /bin/bash --uid ${UID} build && \
    usermod --append --groups wheel build && \
    echo "build ALL=(ALL:ALL) NOPASSWD: /usr/bin/dnf" > /etc/sudoers.d/build

WORKDIR /home/build

USER build
