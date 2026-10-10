# slashman-finance-utils

Shared Taiwan-market (TWSE / TPEx) scraping helpers for the slashman413 finance repos —
`tw-etf-dashboard`, `twse-backtests`, `twse-surge-stocks-dna`, `twse-etf-fa-hermes`.
**Stdlib only**, so a GitHub Actions job needs nothing but one `pip install`.

Every one of those repos carried its own copy of the same code: an SSL context with
verification off, a `fetch_json`, an `sf()` comma-number parser, ROC date maths and a
`STOCK_DAY_ALL` fetcher with an OpenAPI → RWD fallback. This package is that code, once,
with tests.

## Install

```bash
pip install "slashman-finance-utils @ git+https://github.com/slashman413/slashman-finance-utils@v0.1.0"
```

Pin a tag in CI — never `@main`.

## API

```python
from slashman_finance import stock_day_all, stock_names, bwibbu_all, to_float, roc_to_ad, ad_to_roc

data_date, prices = stock_day_all()   # ("1151008", {"2330": {"close","open","high","low","volume"}, ...})
                                      # OpenAPI first, RWD fallback; ({}) on both failing = non-trading day
names = stock_names()                 # {"2330": "台積電", ...}
data_date, val = bwibbu_all()         # {"2330": {"name","pe","div","pb"}, ...}

to_float("1,234.5")   # 1234.5   ('' / '--' / 'N/A' / None -> None)
roc_to_ad("1150612")  # date(2026, 6, 12)
ad_to_roc("2026-06-12", sep="/")  # "115/06/12"
```

Lower level: `slashman_finance.http.fetch_json / fetch_text`, and the pure parsers
`twse.parse_stock_day_openapi`, `twse.parse_stock_day_rwd`, `twse.parse_bwibbu` (handy for
tests that feed recorded payloads).

## Known upstream quirk (why the RWD parser exists)

As of 2026-10 the TWSE RWD endpoint
`/rwd/zh/afterTrading/STOCK_DAY_ALL?response=json` returns **CSV** (with a leading
`日期` column), not JSON. Every hand-rolled fallback in the fleet calls `json.loads` on it
and silently returns `{}`. `parse_stock_day_rwd` accepts both the CSV and the legacy JSON
shape and always returns the date in ROC form.

## Tests

```bash
python -m unittest discover -s tests -v
```

Offline: fixtures under `tests/fixtures/` were recorded from the live endpoints on
2026-10-10.

## Adding to it

Only move code here once **two or more** repos need it. Keep it stdlib-only; keep parsers
pure (payload in → dict out) and give each one a recorded fixture.

---

Built by [@slashman413](https://github.com/slashman413) · [Support on Ko-fi](https://ko-fi.com/ytstories0413)
