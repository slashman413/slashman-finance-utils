"""TWSE (上市) endpoints used across the finance repos."""
import csv
import io
import json
from datetime import date

from .http import fetch_json, fetch_text
from .parse import ad_to_roc, to_float

OPENAPI = "https://openapi.twse.com.tw/v1"
RWD = "https://www.twse.com.tw/rwd/zh"


def _quote(open_, high, low, close, volume):
    """Build a quote dict, or None when the close is missing (suspended / no trade)."""
    c = to_float(close)
    if not c:
        return None
    vals = [to_float(x) for x in (open_, high, low, volume)]
    if any(v is None for v in vals):
        return None
    o, h, l, v = vals
    return {"close": c, "open": o, "high": h, "low": l, "volume": v}


def parse_stock_day_openapi(rows):
    """OpenAPI STOCK_DAY_ALL rows -> (data_date_roc, {code: quote}), names separately."""
    prices, names = {}, {}
    for row in rows:
        code = str(row.get("Code", "")).strip()
        if not code:
            continue
        names[code] = row.get("Name", code)
        q = _quote(row.get("OpeningPrice"), row.get("HighestPrice"), row.get("LowestPrice"),
                   row.get("ClosingPrice"), row.get("TradeVolume"))
        if q:
            prices[code] = q
    data_date = str(rows[0].get("Date", "")) if rows else ""
    return data_date, prices, names


def parse_stock_day_rwd(body):
    """RWD STOCK_DAY_ALL body -> (data_date_roc, {code: quote}, names).

    The endpoint has served two shapes:
      * JSON (until ~2026): {"date": "YYYYMMDD", "data": [[code, name, vol, value,
        open, high, low, close, ...], ...]}
      * CSV (observed 2026-10, even with response=json): header row
        日期,證券代號,證券名稱,成交股數,成交金額,開盤價,最高價,最低價,收盤價,...
    Both are normalised here; the date is always returned in ROC form.
    """
    if isinstance(body, str):
        stripped = body.lstrip()
        body = json.loads(stripped) if stripped.startswith("{") else stripped
    prices, names = {}, {}
    if isinstance(body, dict):
        for r in body.get("data", []):
            if len(r) < 8:
                continue
            code = str(r[0]).strip()
            names[code] = str(r[1]).strip()
            q = _quote(r[4], r[5], r[6], r[7], r[2])
            if q:
                prices[code] = q
        raw = body.get("date", "")
        return (ad_to_roc(raw) if raw else ""), prices, names

    data_date = ""
    for row in csv.DictReader(io.StringIO(body)):
        code = (row.get("證券代號") or "").strip()
        if not code:
            continue
        data_date = data_date or (row.get("日期") or "").strip()
        names[code] = (row.get("證券名稱") or code).strip()
        q = _quote(row.get("開盤價"), row.get("最高價"), row.get("最低價"),
                   row.get("收盤價"), row.get("成交股數"))
        if q:
            prices[code] = q
    return data_date, prices, names


def stock_day_all(on_date=None, *, fallback=True, timeout=30, log=print):
    """Latest daily OHLCV for every TWSE-listed security.

    Tries the OpenAPI first, then the RWD endpoint for `on_date` (default today).
    Returns (data_date_roc, {code: {close, open, high, low, volume}}); ({}) when both fail
    — callers treat an empty dict as "non-trading day".
    """
    try:
        rows = fetch_json(f"{OPENAPI}/exchangeReport/STOCK_DAY_ALL", timeout=timeout)
        if not rows:
            raise ValueError("empty")
        data_date, prices, _ = parse_stock_day_openapi(rows)
        return data_date, prices
    except Exception as e:
        if not fallback:
            raise
        log(f"  OpenAPI STOCK_DAY_ALL failed: {e}, trying RWD...")
    d = on_date or date.today()
    try:
        body = fetch_text(f"{RWD}/afterTrading/STOCK_DAY_ALL?response=json&date={d:%Y%m%d}",
                          timeout=timeout)
        data_date, prices, _ = parse_stock_day_rwd(body)
        return data_date or ad_to_roc(d), prices
    except Exception as e:
        log(f"  RWD STOCK_DAY_ALL failed: {e}")
        return ad_to_roc(d), {}


def stock_names(timeout=30):
    """{code: 中文名稱} for every TWSE-listed security (OpenAPI STOCK_DAY_ALL)."""
    rows = fetch_json(f"{OPENAPI}/exchangeReport/STOCK_DAY_ALL", timeout=timeout)
    return parse_stock_day_openapi(rows)[2]


def parse_bwibbu(rows):
    out = {}
    for r in rows:
        code = r.get("Code")
        if not code:
            continue
        out[code] = {"name": r.get("Name", code),
                     "pe": to_float(r.get("PEratio")),
                     "div": to_float(r.get("DividendYield")),
                     "pb": to_float(r.get("PBratio"))}
    data_date = str(rows[0].get("Date", "")) if rows else ""
    return data_date, out


def bwibbu_all(timeout=30):
    """BWIBBU_ALL valuation snapshot -> (data_date_roc, {code: {name, pe, div, pb}})."""
    rows = fetch_json(f"{OPENAPI}/exchangeReport/BWIBBU_ALL", timeout=timeout)
    if not rows:
        raise ValueError("BWIBBU_ALL returned no rows")
    return parse_bwibbu(rows)
