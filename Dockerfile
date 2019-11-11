FROM python:3.7-alpine
# need Git for pbr to install from source checkout w/o sdist tarball
RUN apk update && apk add --no-cache --virtual build_deps git build-base libffi-dev openssl-dev
ADD . /opt/operator
RUN /opt/operator/install.sh --no-cache-dir /opt/operator
RUN apk del build_deps
