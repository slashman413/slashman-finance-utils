import json
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from slashman_finance import twse

FIX = Path(__file__).parent / "fixtures"


def _read(name):
    return (FIX / name).read_text(encoding="utf-8")


class StockDayParsers(unittest.TestCase):
    def test_openapi(self):
        data_date, prices, names = twse.parse_stock_day_openapi(json.loads(_read("stock_day_all_openapi.json")))
        self.assertEqual(data_date, "1151008")
        self.assertEqual(prices["2330"]["close"], 2550.0)
        self.assertEqual(prices["0050"]["volume"], 99877876.0)
        self.assertEqual(names["2317"], "鴻海")

    def test_rwd_csv(self):
        data_date, prices, names = twse.parse_stock_day_rwd(_read("stock_day_all_rwd.csv"))
        self.assertEqual(data_date, "1151008")
        self.assertEqual(prices["2330"], {"close": 2550.0, "open": 2550.0, "high": 2575.0,
                                          "low": 2550.0, "volume": 23145193.0})
        self.assertNotIn("9999", prices)           # suspended: '--' close is skipped
        self.assertEqual(names["9999"], "停牌股")    # ...but its name is still known

    def test_rwd_legacy_json(self):
        data_date, prices, _ = twse.parse_stock_day_rwd(_read("stock_day_all_rwd_legacy.json"))
        self.assertEqual(data_date, "1150612")      # AD date normalised to ROC
        self.assertEqual(prices["0050"]["volume"], 1234567.0)
        self.assertNotIn("9999", prices)

    def test_csv_and_openapi_agree(self):
        _, a, _ = twse.parse_stock_day_openapi(json.loads(_read("stock_day_all_openapi.json")))
        _, b, _ = twse.parse_stock_day_rwd(_read("stock_day_all_rwd.csv"))
        for code in ("0050", "2330"):
            self.assertEqual(a[code], b[code])


class StockDayFallback(unittest.TestCase):
    def test_falls_back_to_rwd_csv(self):
        with mock.patch.object(twse, "fetch_json", side_effect=OSError("boom")), \
             mock.patch.object(twse, "fetch_text", return_value=_read("stock_day_all_rwd.csv")) as ft:
            data_date, prices = twse.stock_day_all(date(2026, 10, 8), log=lambda *_: None)
        self.assertIn("date=20261008", ft.call_args.args[0])
        self.assertEqual(data_date, "1151008")
        self.assertIn("2330", prices)

    def test_both_fail_returns_empty(self):
        with mock.patch.object(twse, "fetch_json", side_effect=OSError("a")), \
             mock.patch.object(twse, "fetch_text", side_effect=OSError("b")):
            data_date, prices = twse.stock_day_all(date(2026, 10, 8), log=lambda *_: None)
        self.assertEqual((data_date, prices), ("1151008", {}))

    def test_no_fallback_raises(self):
        with mock.patch.object(twse, "fetch_json", side_effect=OSError("a")):
            with self.assertRaises(OSError):
                twse.stock_day_all(fallback=False)


class Bwibbu(unittest.TestCase):
    def test_parse(self):
        data_date, out = twse.parse_bwibbu(json.loads(_read("bwibbu_all.json")))
        self.assertEqual(data_date, "1151008")
        self.assertEqual(out["2330"], {"name": "台積電", "pe": 29.56, "div": 0.86, "pb": 10.28})
        self.assertIsNone(out["1101"]["pe"])        # loss-making: blank PE


if __name__ == "__main__":
    unittest.main()
