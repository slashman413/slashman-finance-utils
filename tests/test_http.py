import ssl
import unittest
from pathlib import Path
from unittest import mock

from slashman_finance import http


class HostScoping(unittest.TestCase):
    def test_twse_hosts_recognised(self):
        for url in (
            "https://www.twse.com.tw/rwd/zh",
            "https://openapi.twse.com.tw/v1",
            "https://api.tpex.org.tw/x",
        ):
            self.assertTrue(http._is_twse(url), url)

    def test_other_hosts_not_scoped(self):
        self.assertFalse(http._is_twse("https://example.com/x"))
        self.assertFalse(http._is_twse("https://not-twse.com.tw/x"))


class PinnedBundle(unittest.TestCase):
    def test_bundle_exists_and_loads(self):
        ctx = http._pinned_context()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)

    def test_default_context_is_verifying(self):
        ctx = http._default_context()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)


class FallbackBehavior(unittest.TestCase):
    def test_twse_falls_back_to_pinned_bundle(self):
        calls = []

        def fake_urlopen(req, context=None, timeout=None):
            calls.append(context)
            raise ssl.SSLCertVerificationError("incomplete chain")

        with mock.patch.object(http.urllib.request, "urlopen", side_effect=fake_urlopen):
            with self.assertRaises(ssl.SSLCertVerificationError):
                http.fetch_text("https://www.twse.com.tw/rwd/zh")
        # default attempt + one pinned attempt
        self.assertEqual(len(calls), 2)
        for ctx in calls:
            self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_pinned_fallback_succeeds(self):
        calls = []

        def fake_urlopen(req, context=None, timeout=None):
            calls.append(context)
            if len(calls) == 1:
                raise ssl.SSLCertVerificationError("incomplete chain")

            class _Resp:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    return "ok".encode()

            return _Resp()

        with mock.patch.object(http.urllib.request, "urlopen", side_effect=fake_urlopen):
            self.assertEqual(http.fetch_text("https://www.twse.com.tw/rwd/zh", retries=1), "ok")
        self.assertEqual(len(calls), 2)

    def test_non_twse_never_uses_pinned_bundle(self):
        calls = []

        def fake_urlopen(req, context=None, timeout=None):
            calls.append(context)
            raise ssl.SSLCertVerificationError("bad cert")

        with mock.patch.object(http.urllib.request, "urlopen", side_effect=fake_urlopen):
            with self.assertRaises(ssl.SSLCertVerificationError):
                http.fetch_text("https://example.com/x")
        self.assertEqual(len(calls), 1)

    def test_transient_error_retries(self):
        calls = []

        def fake_urlopen(req, context=None, timeout=None):
            calls.append(1)
            raise ConnectionError("network blip")

        with mock.patch.object(http.urllib.request, "urlopen", side_effect=fake_urlopen):
            with self.assertRaises(ConnectionError):
                http.fetch_text("https://example.com/x", retries=2, backoff=0)
        self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()
