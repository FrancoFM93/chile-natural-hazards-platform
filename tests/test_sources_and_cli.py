import hashlib
import json
from pathlib import Path

import pytest
import requests

from source_profiler.__main__ import main
from source_profiler.sources import ENDPOINTS, TIMEOUT, capture, decode_features


FIXTURES = Path(__file__).parent / "fixtures"
BASE_ARGS = ["--start", "2020-01-01", "--end", "2020-01-02", "--bbox", "-80", "-60", "-60", "-15", "--min-magnitude", "4.5"]


def fake_response(monkeypatch, body, status=200):
    response = requests.Response()
    response.status_code = status
    response._content = body
    response.url = "https://example.test/query"
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return response
    monkeypatch.setattr(requests, "get", get)
    return calls


@pytest.mark.parametrize("provider", ["usgs", "emsc"])
def test_http_parameters_timeout_and_exact_payload_preservation(monkeypatch, tmp_path, query, provider):
    body = b'{ "type": "FeatureCollection", "features": [] }\r\n'
    calls = fake_response(monkeypatch, body)
    result, metadata = capture(provider, query, tmp_path)
    assert result == (tmp_path / f"{provider}.raw.json").read_bytes() == body
    assert metadata["sha256"] == hashlib.sha256(body).hexdigest()
    url, kwargs = calls[0]
    assert url == ENDPOINTS[provider]
    assert kwargs["timeout"] == TIMEOUT
    params = kwargs["params"]
    assert params["format"] == ("geojson" if provider == "usgs" else "json")
    assert params["starttime"] == "2020-01-01T00:00:00Z"
    assert params["endtime"] == "2020-01-02T00:00:00Z"
    assert params["minlatitude"] == -60
    assert params["maxlatitude"] == -15
    assert params["minlongitude"] == -80
    assert params["maxlongitude"] == -60
    assert params["minmagnitude"] == 4.5


def test_http_failure_payload_preserved(monkeypatch, tmp_path, query):
    body = b"provider failure, not JSON\r\n"
    fake_response(monkeypatch, body, 503)
    _, metadata = capture("usgs", query, tmp_path)
    assert (tmp_path / "usgs.raw.json").read_bytes() == body
    assert metadata["error"]
    assert metadata["status_code"] == 503


def test_timeout_is_reported_without_fabricated_raw_data(monkeypatch, tmp_path, query):
    def timeout(*args, **kwargs):
        raise requests.Timeout("read timed out")
    monkeypatch.setattr(requests, "get", timeout)
    body, metadata = capture("emsc", query, tmp_path)
    assert body is None
    assert "timed out" in metadata["error"]
    assert not (tmp_path / "emsc.raw.json").exists()
    assert (tmp_path / "emsc.request.json").exists()


def test_empty_json_and_http_204(monkeypatch, tmp_path, query):
    assert decode_features(b'{"type":"FeatureCollection","features":[]}') == []
    fake_response(monkeypatch, b"", 204)
    body, metadata = capture("emsc", query, tmp_path)
    assert decode_features(body, no_content=metadata["status_code"] == 204) == []
    assert (tmp_path / "emsc.raw.json").read_bytes() == b""


@pytest.mark.parametrize("body", [b"", b"not-json", b"[]", b"{}", b'{"type":"FeatureCollection"}', b'{"type":"FeatureCollection","features":null}'])
def test_invalid_envelopes_are_failures_not_zero_events(body):
    with pytest.raises(ValueError):
        decode_features(body)


def test_offline_cli_outputs_and_fixtures_unchanged(tmp_path):
    output = tmp_path / "run"
    originals = {name: (FIXTURES / f"{name}.json").read_bytes() for name in ("usgs", "emsc")}
    assert main(BASE_ARGS + ["--usgs-fixture", str(FIXTURES / "usgs.json"), "--emsc-fixture", str(FIXTURES / "emsc.json"), "--output", str(output)]) == 0
    profile = json.loads((output / "profile.json").read_text(encoding="utf-8"))
    assert profile["providers"]["usgs"]["event_count"] == 3
    assert profile["providers"]["emsc"]["event_count"] == 2
    for name in originals:
        assert (output / f"{name}.raw.json").read_bytes() == originals[name]
        assert (FIXTURES / f"{name}.json").read_bytes() == originals[name]
    normalized = json.loads((output / "usgs.normalized.json").read_text(encoding="utf-8"))
    assert len(normalized) == 3
    assert normalized[2]["occurred_at_utc"] is None
    assert (output / "report.md").exists()


def test_partial_failure_preserves_raw_and_reports_other_provider(tmp_path):
    bad_fixture = tmp_path / "bad.json"
    bad_fixture.write_bytes(b"broken response\r\n")
    output = tmp_path / "run"
    code = main(BASE_ARGS + ["--usgs-fixture", str(bad_fixture), "--emsc-fixture", str(FIXTURES / "emsc.json"), "--output", str(output)])
    assert code == 1
    assert (output / "usgs.raw.json").read_bytes() == b"broken response\r\n"
    result = json.loads((output / "profile.json").read_text(encoding="utf-8"))["providers"]
    assert result["usgs"]["status"] == "failed"
    assert result["emsc"]["event_count"] == 2
    assert "FAILED (count unknown)" in (output / "report.md").read_text(encoding="utf-8")


def test_existing_output_directory_is_not_overwritten(tmp_path):
    marker = tmp_path / "marker.txt"
    marker.write_text("keep", encoding="utf-8")
    assert main(BASE_ARGS + ["--provider", "usgs", "--usgs-fixture", str(FIXTURES / "usgs.json"), "--output", str(tmp_path)]) == 1
    assert marker.read_text(encoding="utf-8") == "keep"
    assert list(tmp_path.iterdir()) == [marker]


def test_offline_mode_cannot_make_partial_live_requests():
    with pytest.raises(SystemExit) as exc:
        main(BASE_ARGS + ["--usgs-fixture", str(FIXTURES / "usgs.json")])
    assert exc.value.code == 2
