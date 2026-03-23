import datetime
from typing import Optional, Any


def normalize_str(value: str, allow_blank: bool = False) -> Optional[str]:
    string = value.strip()
    if not string and not allow_blank:
        string = None
    return string


def parse_iso8601_utc(value: str) -> Optional[datetime.datetime]:
    ts_raw = value.strip().replace('Z', '+00:00')
    if not ts_raw:
        return None

    try:
        ts = datetime.datetime.fromisoformat(ts_raw)
    except ValueError:
        return None

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=datetime.timezone.utc)

    return ts.astimezone(datetime.timezone.utc).replace(microsecond=0)


def to_iso8601_utc(value: Any) -> Optional[str]:
    """
    Convert a datetime-like value into an ISO-8601 UTC string.
    """
    if value is None:
        return None

    # datetime
    if isinstance(value, datetime.datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        dt = dt.astimezone(datetime.timezone.utc)
        return dt.isoformat()

    # date / time
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()

    # string
    if isinstance(value, str):
        return parse_iso8601_utc(value).isoformat()

    return None
