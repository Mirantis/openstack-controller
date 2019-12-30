FROM python:3.7-alpine as builder
# need Git for pbr to install from source checkout w/o sdist tarball
RUN apk update && apk add --no-cache --virtual build_deps git build-base libffi-dev openssl-dev
ADD . /opt/operator
RUN pip wheel --wheel-dir /opt/wheels /opt/operator/data/*
RUN pip wheel --wheel-dir /opt/wheels --find-links /opt/wheels /opt/operator

from python:3.7-alpine
COPY --from=builder /opt/wheels /opt/wheels
COPY --from=builder /opt/operator/uwsgi.ini /opt/operator/uwsgi.ini
# ADD tools /opt
RUN pip install --no-index --no-cache --find-links /opt/wheels openstack-controller && \
    echo -e "LABELS:\n  IMAGE_TAG: $(pip freeze | awk -F '==' '/^openstack-controller=/ {print $2}')" > /dockerimage_metadata
