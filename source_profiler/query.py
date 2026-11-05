"""Explicit query boundaries shared by fetching and offline checks."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_datetime(value: str, *, assume_utc: bool = False) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        if not assume_utc:
            raise ValueError("timestamp must include a UTC offset or Z")
        parsed = parsed.replace(tzinfo=timezone.utc)
    try:
        return parsed.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError("timestamp outside supported UTC datetime range") from exc


@dataclass(frozen=True)
class Query:
    start: datetime
    end: datetime
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float
    min_magnitude: float

    def __post_init__(self):
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("query timestamps must have a timezone")
        if self.start >= self.end:
            raise ValueError("start must be before end")
        numbers = (
            self.min_latitude, self.max_latitude, self.min_longitude,
            self.max_longitude, self.min_magnitude,
        )
        if not all(math.isfinite(value) for value in numbers):
            raise ValueError("query numbers must be finite")
        if not -90 <= self.min_latitude < self.max_latitude <= 90:
            raise ValueError("latitude bounds must satisfy -90 <= min < max <= 90")
        if not -180 <= self.min_longitude < self.max_longitude <= 180:
            raise ValueError("longitude bounds must satisfy -180 <= min < max <= 180")

    def as_dict(self) -> dict:
        result = asdict(self)
        result.update(start=utc_text(self.start), end=utc_text(self.end))
        return result

    def parameters(self, provider: str) -> dict:
        # Explicit limits make a possibly truncated sample visible in the report.
        return {
            "format": "geojson" if provider == "usgs" else "json",
            "starttime": utc_text(self.start),
            "endtime": utc_text(self.end),
            "minlatitude": self.min_latitude,
            "maxlatitude": self.max_latitude,
            "minlongitude": self.min_longitude,
            "maxlongitude": self.max_longitude,
            "minmagnitude": self.min_magnitude,
            "orderby": "time-asc",
            "limit": 20000,
            "nodata": 204,
        }
