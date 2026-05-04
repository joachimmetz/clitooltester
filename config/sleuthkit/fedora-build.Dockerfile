ARG FEDORA_VERSION=44

FROM clitooltester/fedora${FEDORA_VERSION}-sleuthkit

ARG GIT_REPO="https://github.com/sleuthkit/sleuthkit.git"
ARG GIT_TAG="sleuthkit-4.15.0"

RUN git clone ${GIT_REPO} && \
    cd sleuthkit && \
    git checkout ${GIT_TAG} && \
    ./bootstrap && \
    ./configure && \
    make
