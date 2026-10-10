"""Value parsing for TWSE/TPEx payloads (comma numbers, '--' blanks, ROC dates)."""
from datetime import date

_BLANKS = {"", "--", "---", "N/A", "-"}


def to_float(v):
    """'1,234.5' -> 1234.5; None / '' / '--' / 'N/A' / garbage -> None."""
    if v is None:
        return None
    s = str(v).replace(",", "").strip()
    if s in _BLANKS:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def roc_to_ad(s):
    """'1150612' / '115/06/12' / '115-06-12' (民國) -> date(2026, 6, 12)."""
    digits = "".join(ch for ch in str(s) if ch.isdigit())
    if len(digits) < 6:
        raise ValueError(f"not a ROC date: {s!r}")
    return date(int(digits[:-4]) + 1911, int(digits[-4:-2]), int(digits[-2:]))


def ad_to_roc(d, sep=""):
    """date(2026, 6, 12) or '2026-06-12' / '20260612' -> '1150612' (or '115/06/12' with sep='/')."""
    if not isinstance(d, date):
        digits = "".join(ch for ch in str(d) if ch.isdigit())
        d = date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
    return f"{d.year - 1911}{sep}{d.month:02d}{sep}{d.day:02d}"
