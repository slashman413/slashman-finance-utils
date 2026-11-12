"""HTTP helper shared by all fetchers.

TLS: we always verify.  The system-default (fully verifying) context is tried
first; only when a TWSE/TPEx host rejects a strict handshake because it serves
an incomplete chain do we make one dedicated attempt against the pinned bundle
shipped alongside the package.  The bundle carries the intermediate + root certs
so verification still runs against a known chain — we never disable certificate
checks.
"""
import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

log = logging.getLogger(__name__)

# The only domains we ever relax the chain for.  Everything else stays on the
# system-default verifying context and is never opened with checks disabled.
_TWSE_HOSTS = ("twse.com.tw", "tpex.org.tw")

# Pinned chain (intermediates + root, no leaf) for hosts that omit intermediates.
_BUNDLE_PATH = os.path.join(os.path.dirname(__file__), "certs", "twse-ca-bundle.pem")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _default_context():
    """System-default context with full verification."""
    return ssl.create_default_context()


def _pinned_context():
    """Full-verify context that additionally trusts the pinned TWSE chain."""
    return ssl.create_default_context(cafile=_BUNDLE_PATH)


def _is_twse(url):
    host = urlparse(url).netloc.lower().split(":")[0]
    return any(host == h or host.endswith("." + h) for h in _TWSE_HOSTS)


def _is_cert_error(exc):
    """True when the failure is a TLS certificate-verification problem.

    urlopen may raise ssl.SSLCertVerificationError directly or wrap it in
    urllib.error.URLError.
    """
    if isinstance(exc, ssl.SSLCertVerificationError):
        return True
    if isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, ssl.SSLCertVerificationError):
        return True
    return False


def fetch_text(url, *, timeout=30, retries=0, backoff=2.0, headers=None):
    """GET `url` and return the body as text. Retries transient errors with linear backoff.

    TLS verification is always on.  For TWSE/TPEx hosts that fail strict
    verification (incomplete chain), one dedicated attempt is made against the
    pinned CA bundle before giving up; that attempt is still fully verifying and
    is logged when used.
    """
    req = urllib.request.Request(url, headers=headers or DEFAULT_HEADERS)
    ctx = _default_context()
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
                return r.read().decode("utf-8-sig")
        except ssl.SSLError as e:
            # A cert failure won't fix itself by re-hitting the same context.
            last_err = e
            break
        except Exception as e:
            last_err = e
            if attempt == retries:
                break
            time.sleep(backoff * (attempt + 1))
    # Default context gave up on a certificate error: for TWSE/TPEx, try the
    # pinned bundle once (still fully verifying) before giving up.
    if last_err is not None and _is_cert_error(last_err) and _is_twse(url):
        log.warning(
            "TLS strict verify failed for %s; retrying with pinned TWSE CA bundle", url
        )
        try:
            with urllib.request.urlopen(req, context=_pinned_context(), timeout=timeout) as r:
                return r.read().decode("utf-8-sig")
        except Exception:
            raise
    if last_err is not None:
        raise last_err


def fetch_json(url, **kw):
    """GET `url` and decode JSON (same keyword options as `fetch_text`)."""
    return json.loads(fetch_text(url, **kw))
