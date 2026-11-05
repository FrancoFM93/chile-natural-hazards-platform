import json
from pathlib import Path

import pytest
import requests

from source_profiler.query import Query, parse_datetime


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("unit tests must not access live APIs")
    monkeypatch.setattr(requests.sessions.Session, "request", blocked)


@pytest.fixture
def query():
    return Query(
        parse_datetime("2020-01-01", assume_utc=True),
        parse_datetime("2020-01-02", assume_utc=True),
        -60, -15, -80, -60, 4.5,
    )


@pytest.fixture
def features():
    return {name: json.loads((FIXTURES / f"{name}.json").read_bytes())["features"] for name in ("usgs", "emsc")}
