import datetime
from typing import Optional


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
