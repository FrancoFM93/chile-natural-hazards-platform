from dataclasses import replace

import pytest

from source_profiler.profiling import check_boundaries, profile, render_report
from source_profiler.query import parse_datetime


def test_schema_missingness_and_types_from_fixtures(features, query):
    records, summary = profile("usgs", features["usgs"], query)
    assert len(records) == summary["event_count"] == 3
    assert summary["records_with_errors"] == 1
    assert summary["source_fields"]["id"]["types"] == {"integer": 1, "string": 2}
    assert summary["source_fields"]["properties.mag"]["types"] == {"null": 1, "number": 1, "string": 1}
    assert summary["source_fields"]["properties.magType"]["absent"] == 1
    assert summary["source_fields"]["properties.magType"]["blank"] == 1
    assert summary["normalized_fields"]["magnitude_type"]["missing"] == 2
    assert summary["timestamp_ranges"]["occurred_at_utc"] == {
        "min": "2020-01-01T00:00:00.123000Z", "max": "2020-01-01T00:00:01Z",
    }
    assert summary["outside_query"] == []
    assert summary["unchecked_boundaries"]


def test_outside_all_requested_boundaries_are_reported(features, query):
    records, summary = profile("emsc", features["emsc"], query)
    assert len(records) == 2  # Out-of-bounds observations are retained.
    assert summary["outside_query"] == [{
        "source_index": 1, "provider_event_id": "synthetic-emsc-outside",
        "fields": ["occurred_at_utc", "latitude", "longitude", "magnitude"],
    }]
    assert summary["unchecked_boundaries"] == []


@pytest.mark.parametrize("time, latitude, longitude", [
    ("2020-01-01T00:00:00Z", -60, -80),
    ("2020-01-02T00:00:00Z", -15, -60),
])
def test_exact_boundaries_are_inclusive(query, time, latitude, longitude):
    assert check_boundaries({"occurred_at_utc": time, "latitude": latitude, "longitude": longitude, "magnitude": 4.5}, query) == ([], [])


def test_empty_profile(query):
    records, summary = profile("emsc", [], query)
    assert records == []
    assert summary["event_count"] == 0
    assert summary["source_fields"]["properties.depth"]["missing"] == 0
    assert summary["timestamp_ranges"]["occurred_at_utc"] == {"min": None, "max": None}


def test_report_contains_findings(features, query):
    _, summary = profile("emsc", features["emsc"], query)
    summary["capture"] = {"mode": "fixture", "query_provenance": "unverified fixture boundaries", "raw_file": "emsc.raw.json"}
    report = render_report(query, {"emsc": summary})
    for text in ("Counts by provider", "Source fields", "Normalized fields", "Timestamp ranges", "synthetic-emsc-outside", "not matched earthquakes", "lastupdate", "unverified fixture"):
        assert text in report


@pytest.mark.parametrize("changes", [
    {"min_latitude": -100}, {"max_longitude": 190}, {"min_magnitude": float("nan")},
    {"min_longitude": -50}, {"end": parse_datetime("2019-01-01T00:00:00Z")},
])
def test_invalid_query_configuration(query, changes):
    with pytest.raises(ValueError):
        replace(query, **changes)
