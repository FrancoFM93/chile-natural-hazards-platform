"""Capture response bodies before parsing, including unsuccessful responses."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import requests

from .query import Query, utc_text


ENDPOINTS = {
    "usgs": "https://earthquake.usgs.gov/fdsnws/event/1/query",
    "emsc": "https://www.seismicportal.eu/fdsnws/event/1/query",
}
TIMEOUT = (10, 30)  # connect and read timeouts in seconds


def write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def capture(provider: str, query: Query, output: Path, fixture: Path | None = None):
    """Return (body, metadata). A transport error has no body to preserve."""
    metadata = {
        "provider": provider,
        "mode": "fixture" if fixture else "live",
        "captured_at_utc": utc_text(datetime.now(timezone.utc)),
        "endpoint": ENDPOINTS[provider],
        "parameters": query.parameters(provider),
        "fixture_path": str(fixture.resolve()) if fixture else None,
        "query_provenance": "unverified fixture boundaries" if fixture else "sent to provider",
    }
    body = None
    try:
        if fixture is not None:
            body = fixture.read_bytes()
        else:
            with requests.get(
                ENDPOINTS[provider], params=metadata["parameters"], timeout=TIMEOUT,
                headers={"Accept": "application/json", "Accept-Encoding": "identity"},
            ) as response:
                body = response.content
                metadata.update(
                    status_code=response.status_code, request_url=response.url,
                    content_type=response.headers.get("Content-Type"),
                )
                # Save the original payload even when raise_for_status() fails.
                raw_path = output / f"{provider}.raw.json"
                raw_path.write_bytes(body)
                response.raise_for_status()
                if response.status_code not in (200, 204):
                    metadata["error"] = f"unexpected HTTP status {response.status_code}"
    except (requests.RequestException, OSError) as exc:
        metadata["error"] = str(exc)

    if body is not None:
        raw_path = output / f"{provider}.raw.json"
        if fixture is not None:
            raw_path.write_bytes(body)
        metadata.update(raw_file=raw_path.name, sha256=hashlib.sha256(body).hexdigest())
    write_json(output / f"{provider}.request.json", metadata)
    return body, metadata


def decode_features(body: bytes, *, no_content: bool = False) -> list:
    if no_content:
        if body.strip():
            raise ValueError("HTTP 204 unexpectedly contained a body")
        return []
    try:
        document = json.loads(body)
    except (ValueError, UnicodeError) as exc:
        raise ValueError(f"response is not valid JSON: {exc}") from exc
    if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
        raise ValueError("expected a GeoJSON FeatureCollection object")
    if not isinstance(document.get("features"), list):
        raise ValueError("FeatureCollection.features must be an array")
    return document["features"]
