import unittest
from datetime import date

from slashman_finance.parse import ad_to_roc, roc_to_ad, to_float


class ToFloat(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(to_float("1,234.5"), 1234.5)
        self.assertEqual(to_float(" 12 "), 12.0)
        self.assertEqual(to_float(3), 3.0)

    def test_blanks(self):
        for v in (None, "", "--", "N/A", "-", "abc"):
            self.assertIsNone(to_float(v), v)


class RocDates(unittest.TestCase):
    def test_roc_to_ad(self):
        self.assertEqual(roc_to_ad("1150612"), date(2026, 6, 12))
        self.assertEqual(roc_to_ad("115/06/12"), date(2026, 6, 12))
        self.assertEqual(roc_to_ad("99/01/02"), date(2010, 1, 2))

    def test_ad_to_roc(self):
        self.assertEqual(ad_to_roc(date(2026, 6, 12)), "1150612")
        self.assertEqual(ad_to_roc("20260612"), "1150612")
        self.assertEqual(ad_to_roc("2026-06-12", sep="/"), "115/06/12")

    def test_bad_roc(self):
        with self.assertRaises(ValueError):
            roc_to_ad("115")


if __name__ == "__main__":
    unittest.main()
