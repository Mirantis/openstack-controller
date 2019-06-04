FROM python:3.7
ADD . /opt/koshkaas
RUN pip install /opt/koshkaas
CMD kopf run -m koshkaas.main
