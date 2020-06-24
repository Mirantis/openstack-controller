ARG FROM=docker-remote.docker.mirantis.net/ubuntu:bionic
FROM $FROM as builder
# NOTE(pas-ha) need Git for pbr to install from source checkout w/o sdist
ADD https://bootstrap.pypa.io/get-pip.py /tmp/get-pip.py
RUN apt-get update; \
    apt-get install -y \
        python3-distutils \
        build-essential \
        python3.7-dev \
        libffi-dev \
        libssl-dev \
        git; \
    python3.7 /tmp/get-pip.py
ADD . /opt/operator
RUN pip wheel --wheel-dir /opt/wheels --find-links /opt/wheels /opt/operator

FROM $FROM
COPY --from=builder /tmp/get-pip.py /tmp/get-pip.py
COPY --from=builder /opt/wheels /opt/wheels
COPY --from=builder /opt/operator/uwsgi.ini /opt/operator/uwsgi.ini
ADD kopf-session-timeout.path /tmp/kopf-session-timeout.path
# NOTE(pas-ha) apt-get download + dpkg-deb -x is a dirty hack
# to fetch distutils w/o pulling in most of python3.6
# FIXME(pas-ha) strace/gdb is installed only temporary for now for debugging
RUN set -ex; \
    apt-get -q update; \
    apt-get install -q -y --no-install-recommends --no-upgrade \
        python3.7 \
        python3.7-dbg \
        libpython3.7 \
        gdb \
        patch \
        strace \
        ca-certificates; \
    apt-get download python3-distutils; \
    dpkg-deb -x python3-distutils*.deb /; \
    rm -vf python3-distutils*.deb; \
    python3.7 /tmp/get-pip.py; \
    pip install --no-index --no-cache --find-links /opt/wheels openstack-controller; \
    cd /usr/local/lib/python3.7/dist-packages; \
    patch -p1 < /tmp/kopf-session-timeout.path; \
    cd -
RUN rm -rvf /tmp/kopf-session-timeout.path
RUN rm -rvf /opt/wheels; \
    apt-get -q clean; \
    rm -rvf /var/lib/apt/lists/*; \
    sh -c "echo \"LABELS:\n  IMAGE_TAG: $(pip freeze | awk -F '==' '/^openstack-controller=/ {print $2}')\" > /dockerimage_metadata"
