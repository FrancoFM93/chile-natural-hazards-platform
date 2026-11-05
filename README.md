# chile-natural-hazards-platform
Cloud-native data platform for monitoring and analyzing natural hazards affecting Chile using Microsoft Fabric and Azure.

The current milestone is **Data Source Discovery**. The local earthquake source
profiler explores USGS and EMSC responses without requiring any cloud services.
It preserves source payloads, normalizes exploratory records, and reports schema
and quality differences. It does not implement the platform's ingestion pipeline.

## Install and test

Use Python 3.11 or newer. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

On Linux/macOS, use `.venv/bin/python` in place of
`.\.venv\Scripts\python.exe`. For running without tests, install
`requirements.txt` instead.

## Run offline

This example uses synthetic fixtures, including missing fields, malformed values,
and an EMSC observation outside all four query filters:

```powershell
.\.venv\Scripts\python.exe -m source_profiler --start 2020-01-01 --end 2020-01-02 --bbox -80 -60 -60 -15 --min-magnitude 4.5 --usgs-fixture tests/fixtures/usgs.json --emsc-fixture tests/fixtures/emsc.json --output artifacts/offline-example
```

Open `artifacts/offline-example/report.md`. Choose a new output directory for
each run; existing directories are protected from overwriting.

## Fetch from both providers

```powershell
.\.venv\Scripts\python.exe -m source_profiler --start 2020-01-01 --end 2020-01-02 --bbox -80 -60 -60 -15 --min-magnitude 4.5 --output artifacts/live-example
```

`--bbox` takes **minimum longitude, minimum latitude, maximum longitude,
maximum latitude**. Date-only query inputs mean midnight UTC; `--end 2020-01-02`
does not include the rest of January 2. Use `--provider usgs` or `--provider emsc`
to profile one source.

See [Source profiler](docs/source-profiling.md) for output formats, normalization
rules, query semantics, limitations, and findings that need human review.
