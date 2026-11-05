# Earthquake Source Profiler

## Purpose and scope

This Milestone 2 tool makes the source assessment repeatable. It fetches a small
sample from USGS and EMSC, preserves the response body, and compares source
schemas and data quality. The exploratory output is not a final canonical model.

It uses Python 3.11+, the standard library, and `requests`; tests use `pytest`.
Installation, live execution, offline execution, and test commands are in the
[repository README](../README.md). All commands run from the repository root;
no package installation of the local code is needed.

The tool deliberately does not match or deduplicate earthquakes, reconcile
conflicting observations, select a better provider, enrich locations, ingest
incremental updates, schedule requests, or provision cloud resources. It has no
Spark, Pandas, database, Docker, Azure, or Fabric dependency.

## Query behavior

`python -m source_profiler --help` lists all options.

- `--start` and `--end` are required ISO dates or datetimes. Query inputs without
  a timezone are interpreted as UTC. Explicit offsets are converted to UTC.
- Endpoints receive explicit UTC datetimes, never an ambiguous date-only string.
  An end date denotes the start of that day, not its end. The tool checks time,
  latitude, longitude, and minimum magnitude using inclusive bounds.
- `--bbox MIN_LON MIN_LAT MAX_LON MAX_LAT` is required. Bounds must be ordered,
  within [-180, 180] longitude and [-90, 90] latitude. Antimeridian-crossing boxes
  and wrapped longitude ranges are outside this tool's scope.
- `--min-magnitude` is required. No magnitude scale filter is applied. Different
  scales and provider choices of preferred magnitude still affect results.
- Each provider gets one request, `orderby=time-asc`, `limit=20000`, and
  `nodata=204`. A sample at the result limit is explicitly flagged. There is no
  pagination, retry loop, or completeness claim; use small date windows.
- HTTP connect/read timeouts are 10/30 seconds. These are socket timeouts, not
  a maximum total runtime. HTTP errors and transport failures are reported.
- Counts describe all returned features, including invalid records and records
  outside the requested boundaries. The profiler never filters them away.

Both providers document start/end limits as on or after / on or before. Some
numeric filter descriptions differ in whether they explicitly include equality.
The report uses an inclusive checking convention, not a claim that every
provider implements every edge identically. Catalog coverage, revisions,
preferred origins, magnitude scales, and result limits must be reviewed before
comparing counts. Equal counts do not establish that the same events were found.

## Files written

Each run creates a new output directory, defaulting to a UTC timestamp under
`artifacts/`. The directory must not already exist. Generated outputs and local
development tools are ignored by Git.

| File | Meaning |
| --- | --- |
| `<provider>.raw.json` | Unmodified response-body bytes, or an exact copy of the fixture |
| `<provider>.request.json` | Provider, capture time, endpoint, parameters, live HTTP status/URL, fixture path where applicable, SHA-256, and capture errors |
| `<provider>.normalized.json` | Array containing one exploratory row per source feature, including malformed features |
| `profile.json` | Query configuration, source/normalized field statistics, timestamp ranges, indexed issues, boundary checks, capture metadata |
| `report.md` | Human-readable comparison and quality findings |

Raw JSON is never parsed and reserialized for preservation. Live raw files are
written before HTTP status checks or JSON decoding. Error bodies can therefore
contain HTML or text despite the `.json` suffix. `requests` exposes decoded HTTP
content if a server applies content encoding; this is body preservation, not a
capture of wire-level HTTP packets. An HTTP 204 body remains zero bytes; no
synthetic FeatureCollection is written over it. A transport failure has no body
and therefore no raw file.

Each normalized row has `provider`, `provider_event_id`, `occurred_at_utc`,
`updated_at_utc`, `magnitude`, `magnitude_type`, `latitude`, `longitude`, `depth_km`,
and a zero-based `source_index`. That index refers to `features[index]` in the
raw file; issues use the same index. This keeps original values distinct from
normalized values even when an event ID is malformed or missing.

## Normalization rules for review

| Normalized field | USGS source | EMSC source |
| --- | --- | --- |
| `provider_event_id` | `id` | `properties.unid` |
| `occurred_at_utc` | `properties.time`, Unix milliseconds | `properties.time`, ISO 8601 datetime |
| `updated_at_utc` | `properties.updated`, Unix milliseconds | `properties.lastupdate`, ISO 8601 datetime |
| `magnitude` | `properties.mag` | `properties.mag` |
| `magnitude_type` | `properties.magType` | `properties.magtype` |
| `latitude` | `geometry.coordinates[1]` | `geometry.coordinates[1]` |
| `longitude` | `geometry.coordinates[0]` | `geometry.coordinates[0]` |
| `depth_km` | `geometry.coordinates[2]` | `properties.depth` |

- Unix milliseconds are added to a UTC epoch without truncating milliseconds.
  ISO datetimes must contain a time and explicit timezone; timezone-free source
  timestamps are flagged rather than assigned a timezone. Output is ISO UTC
  with `Z`. This is intentionally stricter than the handling of query inputs.
- The provider event ID, occurrence timestamp, latitude, and longitude are
  required for exploratory validation. A Feature object, properties object,
  and Point geometry are also required. These are this tool's validation rules,
  not a declaration of the providers' full schema contracts.
- Update time, magnitude, scale, and depth are optional. Absent/null values
  stay null and appear in missing-value statistics. Malformed non-null optional
  values become null with a warning. There are no default scales or depths.
- Numeric values must be finite JSON numbers. Numeric strings and booleans
  produce validation issues rather than being coerced. Coordinates must fall
  within ordinary latitude/longitude ranges. IDs and scales preserve spelling
  and case; blank strings are invalid.
- Depths remain signed kilometers from the selected provider field. Negative
  depths trigger review warnings and remain negative. No `abs()`, sign reversal,
  EMSC geometry-Z fallback, or inference from inspected examples is used.
- EMSC `lastupdate` is described as publication time. Mapping it to the
  exploratory `updated_at_utc` column does not establish equivalence to USGS
  update metadata. A publication/update time before occurrence is flagged.

Every feature produces a row, including non-object features. Invalid fields
become null and receive indexed issues; other parseable values are retained.
These rows are observations for investigation, not trusted analytical records.
Required/structural errors and optional warnings are counted separately in the
report. Invalid envelopes fail the provider analysis and are not labeled as an
empty catalog. Other selected providers are still processed.

## Offline analysis and tests

When any fixture is supplied, every selected provider must have a fixture.
This mode never falls back to a live request. To analyze only EMSC, use
`--provider emsc --emsc-fixture PATH` with the normal query arguments. Saved raw
JSON responses can be replayed in the same way. Offline query arguments are
checking criteria; they do not prove which filters originally produced a file.
The report labels fixture query provenance as unverified.

The included fixtures are **synthetic**, not the manually retrieved October 2026
records and not evidence of real catalog coverage. They deliberately contain
different depth representations, missing optional fields, malformed values,
and an out-of-bounds observation. The offline example returns three USGS rows
(one with required-field errors) and two EMSC rows (one outside time, latitude,
longitude, and magnitude filters).

Unit tests block HTTP requests and cover normalization, missing/malformed values,
empty responses, field profiling, boundary checks, byte preservation, timeout and
HTTP errors, and CLI outputs. Mock responses test live behavior without APIs.
An empty FeatureCollection is a valid offline input; an empty file alone is
ambiguous and fails JSON parsing. Replaying a live HTTP 204 as an offline empty
file is not supported because fixture mode does not read HTTP sidecars.

Exit code 0 means all selected responses were analyzed; data-quality issues may
still exist. Exit code 1 means a provider or output operation failed. Invalid
CLI arguments use argparse's exit code 2. Inspect `report.md` even after a
successful run, and inspect raw/error files after a failure.

## Limitations and human review

Source statistics cover fields observed across all records plus expected mapped
fields even if absent everywhere. Containers and indexed array elements are
shown separately. Absent fields, nulls, and blank strings are counted separately;
`missing` is their sum. Empty containers are typed, not classified as missing.
Observed source types remain distinct from normalized types. A normalized null
can mean either a source null/absence or a validation failure; inspect the raw
row and issues to distinguish them. Timestamp ranges use every successfully
parsed timestamp, including rows that failed other validation checks.

Findings to review before the canonical model or matching work:

1. Reproduce the assessment's out-of-range EMSC observation with saved query
   parameters. This tool detects such observations but does not establish why
   they occur or automatically correct provider filtering.
2. Confirm depth references, units, and signs for additional catalog samples.
   EMSC documentation defines its depth property, but the geometry-Z sign
   relationship is not established here. The original Z remains in raw data
   and source field statistics.
3. Review identifier stability and update/publication semantics across repeated
   snapshots. No shared ID or revision contract is inferred.
4. Determine legitimate missing fields and magnitude-scale differences over a
   representative period. Small fixtures cannot establish a provider contract.
5. Review observations that cannot be checked against a boundary because a
   required value or magnitude is missing/invalid. They are not counted as
   compliant or automatically excluded.

This tool loads one response per provider into memory and profiles all observed
paths. It is intended for small samples. It does not assess identifier stability,
deduplicate revisions, verify property-coordinate agreement, or model uncertainty.
Source dot-path statistics assume normal provider field names, without literal
dots/brackets in keys. Raw files remain the authority for exact source structure.

## Official references

- [USGS FDSN Event API](https://earthquake.usgs.gov/fdsnws/event/1/): endpoints, formats, filters, no-data behavior and limits.
- [USGS GeoJSON format](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php): field names and coordinate order.
- [EMSC FDSN service](https://www.seismicportal.eu/fdsn-wsevent.html) and [OpenAPI documentation](https://www.seismicportal.eu/fdsnws/event/1/redoc): query semantics and limits.
- [EMSC service specification, v1.1](https://www.emsc-csem.org/Files/epos/specifications/Specs_fdsnevent-WS.pdf): JSON depth and publication metadata definitions. Its field list is not exhaustive for the inspected response; `unid` follows the repository assessment and fixtures.

References reviewed on 2026-11-04. Documentation and observed responses should be
reviewed together when a provider changes its interface.
