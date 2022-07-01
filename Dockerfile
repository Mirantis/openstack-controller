ARG FROM=docker-remote.docker.mirantis.net/ubuntu:focal

FROM $FROM as builder
# NOTE(pas-ha) need Git for pbr to install from source checkout w/o sdist
ADD https://bootstrap.pypa.io/get-pip.py /tmp/get-pip.py
RUN apt-get update; \
    apt-get install -y \
        python3-distutils \
        build-essential \
        python3.8-dev \
        libffi-dev \
        libssl-dev \
        git; \
    python3.8 /tmp/get-pip.py
ADD . /opt/operator
RUN pip wheel --wheel-dir /opt/wheels --find-links /opt/wheels /opt/operator

FROM $FROM
ARG KUBECTL_BINARY="http://binary.mirantis.com/openstack/bin/utils/kubectl/kubectl-1.18.8-linux"
ARG HELM_BINARY="https://binary.mirantis.com/openstack/bin/utils/helm/helm-v3.6.2-linux-amd64"

COPY --from=builder /tmp/get-pip.py /tmp/get-pip.py
COPY --from=builder /opt/wheels /opt/wheels
COPY --from=builder /opt/operator/uwsgi.ini /opt/operator/uwsgi.ini
ADD kopf-patches /tmp/kopf-patches
# NOTE(pas-ha) apt-get download + dpkg-deb -x is a dirty hack
# to fetch distutils w/o pulling in most of python3.6
# FIXME(pas-ha) strace/gdb is installed only temporary for now for debugging
RUN set -ex; \
    apt-get -q update; \
    apt-get install -q -y --no-install-recommends --no-upgrade \
        python3.8 \
        python3.8-dbg \
        libpython3.8 \
        net-tools \
        gdb \
        patch \
        strace \
        ca-certificates \
        wget \
        git; \
    apt-get download python3-distutils; \
    dpkg-deb -x python3-distutils*.deb /; \
    rm -vf python3-distutils*.deb; \
    python3.8 /tmp/get-pip.py; \
    pip install --no-index --no-cache --find-links /opt/wheels openstack-controller; \
    cd /usr/local/lib/python3.8/dist-packages; \
    for p in $(ls /tmp/kopf-patches/*.patch); do \
         patch -p1 < $p; \
    done;  \
    cd -
RUN wget -q -O /usr/local/bin/helm3 ${HELM_BINARY}; \
    chmod +x /usr/local/bin/helm3
RUN wget -q ${KUBECTL_BINARY} -O /usr/local/bin/kubectl; \
    chmod +x /usr/local/bin/kubectl

RUN rm -rvf /tmp/kopf-patches
RUN rm -rvf /opt/wheels; \
    apt-get -q clean; \
    rm -rvf /var/lib/apt/lists/*; \
    sh -c "echo \"LABELS:\n  IMAGE_TAG: $(pip freeze | awk -F '==' '/^openstack-controller=/ {print $2}')\" > /dockerimage_metadata"
