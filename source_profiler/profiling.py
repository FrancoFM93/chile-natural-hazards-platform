"""Small, transparent schema and quality summaries over every returned record."""

from collections import Counter

from .normalize import SOURCE_FIELDS, flatten, normalize
from .query import Query, parse_datetime


NOTES = [
    "Counts describe returned provider records, not matched earthquakes or catalog completeness.",
    "Query checks use inclusive bounds. Date-only inputs mean 00:00:00 UTC, including end dates.",
    "Provider coverage, preferred origins, magnitude scales, rounding and edge inclusivity may differ; review before comparing counts.",
    "USGS depth uses geometry.coordinates[2] in km; EMSC depth uses properties.depth in km. Signs are retained; EMSC geometry Z is not converted or used as a fallback.",
    "EMSC lastupdate is publication metadata; its equivalence to USGS updated is not established.",
    "Ranges use all successfully parsed timestamps, including rows with other errors. Missing/invalid values cannot establish boundary compliance.",
    "A single request per provider is made, with limit=20000 and no pagination; completeness is not established.",
]


def type_name(value) -> str:
    return {
        type(None): "null", bool: "boolean", int: "integer", float: "number",
        str: "string", list: "array", dict: "object",
    }[type(value)]


def field_stats(rows: list[dict], expected=()) -> dict:
    keys = set(expected)
    for row in rows:
        keys.update(row)
    result = {}
    for key in sorted(keys):
        values = [row[key] for row in rows if key in row]
        absent = len(rows) - len(values)
        null = sum(value is None for value in values)
        blank = sum(isinstance(value, str) and not value.strip() for value in values)
        result[key] = {
            "absent": absent, "null": null, "blank": blank,
            "missing": absent + null + blank,
            "types": dict(sorted(Counter(type_name(value) for value in values).items())),
        }
    return result


def check_boundaries(record: dict, query: Query) -> tuple[list[str], list[str]]:
    violations, unchecked = [], []
    checks = {
        "occurred_at_utc": lambda value: query.start <= parse_datetime(value) <= query.end,
        "latitude": lambda value: query.min_latitude <= value <= query.max_latitude,
        "longitude": lambda value: query.min_longitude <= value <= query.max_longitude,
        "magnitude": lambda value: value >= query.min_magnitude,
    }
    for field, check in checks.items():
        if record[field] is None:
            unchecked.append(field)
        elif not check(record[field]):
            violations.append(field)
    return violations, unchecked


def profile(provider: str, features: list, query: Query) -> tuple[list[dict], dict]:
    records, issues, outside, unchecked = [], [], [], []
    for index, feature in enumerate(features):
        record, record_issues = normalize(provider, feature, index)
        records.append(record)
        issues.extend(record_issues)
        violations, unknown = check_boundaries(record, query)
        reference = {"source_index": index, "provider_event_id": record["provider_event_id"]}
        if violations:
            outside.append({**reference, "fields": violations})
        if unknown:
            unchecked.append({**reference, "fields": unknown})

    ranges = {}
    for field in ("occurred_at_utc", "updated_at_utc"):
        values = sorted((row[field] for row in records if row[field]), key=parse_datetime)
        ranges[field] = {"min": values[0] if values else None, "max": values[-1] if values else None}
    source_rows = [{"$": feature, **flatten(feature)} for feature in features]
    error_rows = {issue["source_index"] for issue in issues if issue["severity"] == "error"}
    warning_rows = {issue["source_index"] for issue in issues if issue["severity"] == "warning"}
    result = {
        "status": "profiled",
        "event_count": len(features),
        "records_with_errors": len(error_rows),
        "records_with_warnings": len(warning_rows),
        "source_fields": field_stats(source_rows, SOURCE_FIELDS[provider].values()),
        "normalized_fields": field_stats(records, ("provider", *SOURCE_FIELDS[provider])),
        "timestamp_ranges": ranges,
        "outside_query": outside,
        "unchecked_boundaries": unchecked,
        "issues": issues,
        "possible_limit_reached": len(features) >= 20000,
    }
    return records, result


def cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_report(query: Query, providers: dict) -> str:
    lines = ["# Earthquake source profile", "", "## Requested query", ""]
    lines.extend(f"- {key}: {value}" for key, value in query.as_dict().items())
    lines.extend(["", "## Reading this report", ""])
    lines.extend(f"- {note}" for note in NOTES)
    lines.extend([
        "", "## Counts by provider", "",
        "| Provider | Returned records | Rows with required/structural errors | Rows with warnings |",
        "| --- | ---: | ---: | ---: |",
    ])
    for provider, summary in providers.items():
        if summary["status"] == "failed":
            lines.append(f"| {provider} | FAILED (count unknown) | — | — |")
        else:
            lines.append(
                f"| {provider} | {summary['event_count']} | {summary['records_with_errors']} | {summary['records_with_warnings']} |"
            )
    for provider, summary in providers.items():
        lines.extend(["", f"## {provider.upper()}", ""])
        capture = summary["capture"]
        lines.append(f"Mode: {capture['mode']}; query provenance: {capture['query_provenance']}.")
        lines.append(f"Raw file: {capture.get('raw_file', 'unavailable')}; source indexes are zero-based positions in `features`.")
        if summary["status"] == "failed":
            lines.extend(["", f"Failure: {cell(summary['error'])}"])
            continue
        if summary["possible_limit_reached"]:
            lines.extend(["", "**Result limit reached: this sample may be truncated. Use a smaller query.**"])
        for title, key in (("Source fields", "source_fields"), ("Normalized fields", "normalized_fields")):
            lines.extend([
                "", f"### {title}", "",
                "Types include nulls. Missing = absent + null + blank strings; expected mapped fields appear even if never observed.",
                "", "| Field | Absent | Null | Blank | Missing | Observed types (count) |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ])
            for field, stats in summary[key].items():
                types = ", ".join(f"{name}: {count}" for name, count in stats["types"].items()) or "none observed"
                lines.append(f"| {cell(field)} | {stats['absent']} | {stats['null']} | {stats['blank']} | {stats['missing']} | {types} |")
        lines.extend(["", "### Timestamp ranges (UTC)", ""])
        for field, bounds in summary["timestamp_ranges"].items():
            lines.append(f"- {field}: {bounds['min'] or 'unavailable'} to {bounds['max'] or 'unavailable'}")
        for title, key in (("Records outside requested boundaries", "outside_query"), ("Boundaries that could not be checked", "unchecked_boundaries")):
            lines.extend(["", f"### {title}", ""])
            if not summary[key]:
                lines.append("None observed.")
            for item in summary[key]:
                lines.append(f"- Source index {item['source_index']}, ID {cell(item['provider_event_id'])}: {', '.join(item['fields'])}")
        lines.extend(["", "### Validation issues requiring review", ""])
        if not summary["issues"]:
            lines.append("None observed. Optional missing values are counted in the field tables.")
        for issue in summary["issues"]:
            lines.append(f"- Index {issue['source_index']} [{issue['severity']}] {cell(issue['field'])}: {cell(issue['message'])}")
    return "\n".join(lines) + "\n"
