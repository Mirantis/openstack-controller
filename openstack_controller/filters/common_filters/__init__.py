from urllib.parse import urlsplit


def update_url_hostname(url, hostname):
    parsed = urlsplit(url)
    new_netloc = hostname
    auth = parsed.username
    if auth:
        if parsed.password:
            auth = f"{auth}:{parsed.password}"
        new_netloc = f"{auth}@{new_netloc}"
    if parsed.port:
        new_netloc = f"{new_netloc}:{parsed.port}"
    return parsed._replace(netloc=new_netloc).geturl()
