"""U.S. equity market session status (pre-market / open / after-hours /
closed), based on NYSE regular hours. Uses the stdlib zoneinfo database so
daylight-saving transitions are handled correctly without a third-party
dependency.

Does NOT account for market holidays (Thanksgiving, Christmas, etc.) --
it will report a weekday holiday as if the market were open. Full holiday
handling would need a maintained calendar; this is a reasonable trade-off
for a status badge rather than something order-routing depends on."""
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")

_PRE_START = dtime(4, 0)
_REGULAR_START = dtime(9, 30)
_REGULAR_END = dtime(16, 0)
_POST_END = dtime(20, 0)


def get_market_status() -> dict:
    now_et = datetime.now(_ET)
    t = now_et.time()
    is_weekday = now_et.weekday() < 5  # Monday=0 ... Sunday=6

    if not is_weekday:
        status, label = "closed", "Closed"
    elif _PRE_START <= t < _REGULAR_START:
        status, label = "pre", "Pre-Market"
    elif _REGULAR_START <= t < _REGULAR_END:
        status, label = "open", "Market Open"
    elif _REGULAR_END <= t < _POST_END:
        status, label = "post", "After Hours"
    else:
        status, label = "closed", "Closed"

    return {
        "status": status,
        "label": label,
        "time_et": now_et.strftime("%H:%M"),
        "note": "NYSE regular hours; does not account for market holidays.",
    }
