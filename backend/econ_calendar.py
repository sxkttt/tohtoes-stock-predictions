"""Static economic-calendar events for the current year. Finnhub's
economic-calendar endpoint is premium-only, so this ships a small
hand-maintained list instead -- FOMC decisions, CPI releases, and the
jobs report (NFP) are all published roughly a year ahead by the Fed/BLS,
so a static list is a reasonable trade-off for a free app.

NEEDS AN ANNUAL REFRESH: the FOMC dates below are the actual scheduled
2026 meetings; CPI/NFP dates are *approximated* from each report's usual
recurrence pattern (CPI ~mid-month, NFP first Friday) rather than pulled
from an official calendar. Verify against federalreserve.gov and bls.gov
before relying on exact dates, and replace this list annually.
"""
from datetime import date, timedelta


def _first_friday(year: int, month: int) -> date:
    d = date(year, month, 1)
    offset = (4 - d.weekday()) % 7  # Monday=0 ... Friday=4
    return d + timedelta(days=offset)


_FOMC_2026 = [
    ("2026-01-27", "2026-01-28"), ("2026-03-17", "2026-03-18"), ("2026-04-28", "2026-04-29"),
    ("2026-06-16", "2026-06-17"), ("2026-07-28", "2026-07-29"), ("2026-09-15", "2026-09-16"),
    ("2026-10-27", "2026-10-28"), ("2026-12-08", "2026-12-09"),
]

EVENTS_2026 = (
    [{"date": d, "type": "fomc", "label": "FOMC Decision"} for pair in _FOMC_2026 for d in pair]
    + [{"date": f"2026-{m:02d}-13", "type": "cpi", "label": "CPI Release"} for m in range(1, 13)]
    + [{"date": _first_friday(2026, m).isoformat(), "type": "nfp", "label": "Jobs Report (NFP)"} for m in range(1, 13)]
)


def upcoming_events(limit: int = 10) -> list[dict]:
    today = date.today().isoformat()
    future = sorted((e for e in EVENTS_2026 if e["date"] >= today), key=lambda e: e["date"])
    return future[:limit]
