from copy import deepcopy

import pytest

from source_profiler.normalize import emsc_timestamp, normalize, usgs_timestamp


@pytest.mark.parametrize("value, expected", [
    (0, "1970-01-01T00:00:00Z"),
    (1577836800123, "2020-01-01T00:00:00.123000Z"),
    (-1, "1969-12-31T23:59:59.999000Z"),
])
def test_usgs_timestamp(value, expected):
    assert usgs_timestamp(value) == expected


@pytest.mark.parametrize("value, expected", [
    ("2020-01-01T00:00:00.123Z", "2020-01-01T00:00:00.123000Z"),
    ("2019-12-31T21:00:00.123-03:00", "2020-01-01T00:00:00.123000Z"),
    ("2020-01-01T00:00:00+00:00", "2020-01-01T00:00:00Z"),
])
def test_emsc_timestamp(value, expected):
    assert emsc_timestamp(value) == expected


@pytest.mark.parametrize("value", [None, True, "123", float("inf"), float("nan"), 10**1000])
def test_invalid_usgs_timestamps(value):
    with pytest.raises(ValueError):
        usgs_timestamp(value)


@pytest.mark.parametrize("value", [None, 123, "invalid", "2020-01-01", "2020-01-01T00:00:00", "2020-02-30T00:00:00Z", "0001-01-01T00:00:00+01:00"])
def test_invalid_emsc_timestamps(value):
    with pytest.raises(ValueError):
        emsc_timestamp(value)


def test_provider_mappings_and_originals_unchanged(features):
    before = deepcopy(features)
    usgs, usgs_issues = normalize("usgs", features["usgs"][0], 0)
    emsc, emsc_issues = normalize("emsc", features["emsc"][0], 0)
    assert usgs["depth_km"] == 107.82
    assert emsc["depth_km"] == 109.3
    assert emsc["provider_event_id"] == "synthetic-emsc-1"
    assert usgs["latitude"] == -30.2
    assert emsc["longitude"] == -70.1
    assert usgs["magnitude_type"] == emsc["magnitude_type"] == "mb"
    assert usgs["updated_at_utc"] == "2020-01-01T01:00:00.456000Z"
    assert emsc["updated_at_utc"] == "2020-01-01T02:00:00.456000Z"
    assert not usgs_issues and not emsc_issues
    assert features == before


@pytest.mark.parametrize("depth", [-7.5, 0, 109.3])
def test_emsc_never_changes_depth_sign_or_uses_geometry_z(features, depth):
    feature = deepcopy(features["emsc"][0])
    feature["properties"]["depth"] = depth
    feature["geometry"]["coordinates"][2] = 777
    record, issues = normalize("emsc", feature, 0)
    assert record["depth_km"] == depth
    assert bool(issues) == (depth < 0)


@pytest.mark.parametrize("provider", ["usgs", "emsc"])
def test_missing_optional_fields(features, provider):
    feature = deepcopy(features[provider][0])
    for key in ("updated", "lastupdate", "mag", "magType", "magtype", "depth"):
        feature["properties"].pop(key, None)
    feature["geometry"]["coordinates"] = feature["geometry"]["coordinates"][:2]
    record, issues = normalize(provider, feature, 0)
    assert not issues
    for field in ("updated_at_utc", "magnitude", "magnitude_type", "depth_km"):
        assert record[field] is None


def test_emsc_missing_depth_does_not_fall_back_to_geometry(features):
    feature = deepcopy(features["emsc"][0])
    del feature["properties"]["depth"]
    record, _ = normalize("emsc", feature, 0)
    assert record["depth_km"] is None


@pytest.mark.parametrize("feature", [None, 12, [], {}, {"properties": []}, {"type": "Feature", "geometry": None}])
def test_malformed_records_are_retained_with_errors(feature):
    record, issues = normalize("usgs", feature, 7)
    assert record["source_index"] == 7
    assert record["provider_event_id"] is None
    assert any(issue["severity"] == "error" for issue in issues)


def test_malformed_required_and_optional_fields(features):
    record, issues = normalize("usgs", features["usgs"][2], 2)
    assert record["provider_event_id"] is None
    assert record["occurred_at_utc"] is None
    assert record["longitude"] is None
    assert record["latitude"] == -35
    assert record["magnitude"] is None
    assert record["magnitude_type"] is None
    assert record["depth_km"] == -2
    assert len([item for item in issues if item["severity"] == "error"]) == 3


def test_nonpoint_geometry_is_not_interpreted(features):
    feature = deepcopy(features["usgs"][0])
    feature["geometry"]["type"] = "LineString"
    record, issues = normalize("usgs", feature, 0)
    assert record["latitude"] is record["longitude"] is record["depth_km"] is None
    assert issues


def test_zero_values_are_not_missing_and_scale_spelling_is_retained(features):
    feature = deepcopy(features["usgs"][0])
    feature["properties"].update(time=0, updated=0, mag=0, magType="Mw")
    feature["geometry"]["coordinates"] = [0, 0, 0]
    record, issues = normalize("usgs", feature, 0)
    assert not issues
    assert all(record[field] == 0 for field in ("latitude", "longitude", "depth_km", "magnitude"))
    assert record["magnitude_type"] == "Mw"


def test_update_preceding_event_is_reported(features):
    feature = deepcopy(features["emsc"][0])
    feature["properties"]["lastupdate"] = "2019-12-31T00:00:00Z"
    record, issues = normalize("emsc", feature, 0)
    assert record["updated_at_utc"] == "2019-12-31T00:00:00Z"
    assert any("precedes" in issue["message"] for issue in issues)
