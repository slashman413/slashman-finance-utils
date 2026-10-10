"""HTTP helper shared by all fetchers.

TWSE/TPEx serve certificates that fail strict verification from some runners, so
every repo in the fleet disabled hostname checks inline. That lives here once.
"""
import json
import ssl
import time
import urllib.request

TWSE_SSL_CTX = ssl.create_default_context()
TWSE_SSL_CTX.check_hostname = False
TWSE_SSL_CTX.verify_mode = ssl.CERT_NONE

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def fetch_text(url, *, timeout=30, retries=0, backoff=2.0, headers=None):
    """GET `url` and return the body as text. Retries `retries` extra times with linear backoff."""
    req = urllib.request.Request(url, headers=headers or DEFAULT_HEADERS)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, context=TWSE_SSL_CTX, timeout=timeout) as r:
                return r.read().decode("utf-8-sig")
        except Exception:
            if attempt == retries:
                raise
            time.sleep(backoff * (attempt + 1))


def fetch_json(url, **kw):
    """GET `url` and decode JSON (same keyword options as `fetch_text`)."""
    return json.loads(fetch_text(url, **kw))
