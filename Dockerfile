FROM python:3.7-alpine
ADD . /opt/operator
# need Git for pbr to install from source checkout w/o sdist tarball
RUN apk update && apk add --no-cache --virtual build_deps git
RUN pip install --no-cache-dir /opt/operator
RUN apk del build_deps
