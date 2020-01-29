import datetime
import kopf


@kopf.on.probe(id="now")
def get_current_timestamp(**kwargs):
    return datetime.datetime.utcnow().isoformat()
