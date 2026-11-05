"""Provider-specific mappings. Never infer a missing scale or reverse depth signs."""

from datetime import datetime, timedelta, timezone
import math

from .query import parse_datetime, utc_text


SOURCE_FIELDS = {
    "usgs": {
        "provider_event_id": "id",
        "occurred_at_utc": "properties.time",
        "updated_at_utc": "properties.updated",
        "magnitude": "properties.mag",
        "magnitude_type": "properties.magType",
        "latitude": "geometry.coordinates[1]",
        "longitude": "geometry.coordinates[0]",
        "depth_km": "geometry.coordinates[2]",
    },
    "emsc": {
        "provider_event_id": "properties.unid",
        "occurred_at_utc": "properties.time",
        "updated_at_utc": "properties.lastupdate",
        "magnitude": "properties.mag",
        "magnitude_type": "properties.magtype",
        "latitude": "geometry.coordinates[1]",
        "longitude": "geometry.coordinates[0]",
        "depth_km": "properties.depth",
    },
}
REQUIRED = {"provider_event_id", "occurred_at_utc", "latitude", "longitude"}


def number(value) -> float:
    if type(value) not in (int, float):
        raise ValueError("expected a JSON number (numeric strings and booleans are invalid)")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError("number is outside supported range") from exc
    if not math.isfinite(result):
        raise ValueError("expected a finite number")
    return result


def text_value(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("expected a nonempty string")
    return value  # Preserve identifiers and magnitude-scale spelling exactly.


def usgs_timestamp(value) -> str:
    number(value)
    try:
        # A fixed UTC epoch avoids local-time conversion and truncation of milliseconds.
        return utc_text(datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=value))
    except (OverflowError, TypeError) as exc:
        raise ValueError("Unix milliseconds outside supported datetime range") from exc


def emsc_timestamp(value) -> str:
    text_value(value)
    if "T" not in value and " " not in value:
        raise ValueError("expected an ISO 8601 datetime, including time and timezone")
    return utc_text(parse_datetime(value))


def flatten(value, prefix: str = "") -> dict:
    """Keep containers and indexed array elements visible when profiling source fields."""
    result = {prefix: value} if prefix else {}
    if isinstance(value, dict):
        for key, item in value.items():
            result.update(flatten(item, f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            result.update(flatten(item, f"{prefix}[{index}]"))
    return result


def normalize(provider: str, feature, index: int) -> tuple[dict, list[dict]]:
    fields = flatten(feature)
    record = {"provider": provider, "source_index": index}
    issues = []

    def issue(field, message, severity="warning"):
        issues.append({"source_index": index, "field": field, "severity": severity, "message": message})

    is_feature = isinstance(feature, dict) and feature.get("type") == "Feature"
    if not is_feature:
        issue("$", "expected a GeoJSON Feature object", "error")
    properties = feature.get("properties") if isinstance(feature, dict) else None
    if not isinstance(properties, dict):
        issue("properties", "expected an object", "error")
    geometry = feature.get("geometry") if isinstance(feature, dict) else None
    is_point = isinstance(geometry, dict) and geometry.get("type") == "Point"
    if not is_point:
        issue("geometry", "expected Point geometry; coordinates will not be interpreted", "error")

    timestamp = usgs_timestamp if provider == "usgs" else emsc_timestamp
    for name, source_path in SOURCE_FIELDS[provider].items():
        value = fields.get(source_path)
        record[name] = None
        severity = "error" if name in REQUIRED else "warning"
        if value is None:
            if name in REQUIRED:
                issue(name, f"required source field missing or null: {source_path}", severity)
            continue
        try:
            if name in ("provider_event_id", "magnitude_type"):
                normalized = text_value(value)
            elif name in ("occurred_at_utc", "updated_at_utc"):
                normalized = timestamp(value)
            else:
                if source_path.startswith("geometry.") and not is_point:
                    raise ValueError("cannot extract coordinates from non-Point geometry")
                normalized = number(value)
                if name == "latitude" and not -90 <= normalized <= 90:
                    raise ValueError("latitude outside [-90, 90]")
                if name == "longitude" and not -180 <= normalized <= 180:
                    raise ValueError("longitude outside [-180, 180]")
            record[name] = normalized
        except ValueError as exc:
            issue(name, f"{source_path}: {exc}", severity)

    if record["depth_km"] is not None and record["depth_km"] < 0:
        issue("depth_km", "negative source depth retained unchanged; review reference and sign")
    if record["occurred_at_utc"] and record["updated_at_utc"]:
        if parse_datetime(record["updated_at_utc"]) < parse_datetime(record["occurred_at_utc"]):
            issue("updated_at_utc", "update/publication time precedes occurrence time")
    return record, issues
