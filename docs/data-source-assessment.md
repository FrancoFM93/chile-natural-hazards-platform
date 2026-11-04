# Data Source Assessment

**Project:** Chile Natural Hazards Intelligence Platform  
**Status:** In progress  
**Last reviewed:** 2026-11-03

## 1. Purpose

Evaluate earthquake data providers for the Chile Natural Hazards Intelligence Platform.

The objective is to identify sources that support reliable, traceable, and maintainable earthquake-data ingestion, with particular attention to Chile.

Provider selection must consider data quality, accessibility, historical coverage, update behavior, licensing, and integration complexity.

## 2. Candidate Providers

### 2.1 USGS Earthquake Catalog

- Organization: United States Geological Survey
- Coverage: Global
- Interface: FDSN Event Web Service
- Format: GeoJSON, XML, and other supported formats
- Geographic filtering: Supported
- Historical queries: Supported
- Incremental updates: `updatedafter`
- Role: Initial reference provider
- Status: Selected for initial investigation

Official documentation: https://earthquake.usgs.gov/fdsnws/event/1/

### 2.2 EMSC SeismicPortal

- Organization: European-Mediterranean Seismological Centre
- Coverage: Global
- Interface: FDSN Event Web Service
- Format: JSON, XML, text
- Geographic filtering: Supported
- Historical queries: Supported
- Incremental updates: `updatedafter`
- Licensing: CC BY 4.0
- Role: Candidate second scientific provider
- Status: Pending live validation

Official documentation: https://www.seismicportal.eu/fdsn-wsevent.html

### 2.3 Centro Sismológico Nacional (CSN)

- Organization: Universidad de Chile
- Coverage: Chile
- Available resources: Recent earthquake information, historical earthquake catalogs, and seismic waveform services
- Geographic relevance: High
- Public catalog export: Available through the historical visualizer
- Documented automated event catalog API: Not yet confirmed
- Usage conditions: Require review before automated redistribution
- Role: Preferred Chilean scientific source
- Status: Under investigation

Official website: https://www.csn.uchile.cl/

Historical catalog: https://owl.csn.uchile.cl/visualizador_csn.html

## 3. Evaluation Criteria

Each provider will be evaluated for:

1. API accessibility and response format
2. Stable earthquake identifiers
3. Occurrence and update timestamps
4. Geographic coordinates and depth
5. Magnitude value and scale
6. Historical data availability
7. Incremental ingestion support
8. Event revision behavior
9. Missing and inconsistent values
10. Rate limits and usage conditions
11. Data provenance
12. Integration complexity

## 4. Initial Strategy

The initial implementation will use USGS.

EMSC will be investigated as a potential second provider to demonstrate multi-source ingestion and event reconciliation.

CSN will be prioritized for further research because it provides an authoritative Chilean scientific context.

No additional provider is approved for implementation until its interface, data contract, and usage conditions have been assessed.

## 5. Open Questions

- Does EMSC provide sufficient overlapping event coverage with USGS for meaningful cross-provider comparison?
- How stable are event identifiers across revisions?
- Can CSN data be retrieved programmatically through a supported event catalog interface?
- Do different providers report magnitude using different scales?
- How should conflicting observations be preserved?
- How should offshore Chilean earthquakes be classified?
- What ingestion frequency is reasonable for the available source interfaces?

## 6. Next Activity

Perform a small, reproducible API exploration using Python.

Save representative responses locally, inspect field types and missing values, and document the differences between providers before defining the canonical earthquake model.

## 7. Initial API Exploration Results

**Date:** 2026-11-04  
**Sources:** USGS Earthquake Catalog and EMSC SeismicPortal  
**Geographic scope:** Approximate Chile monitoring bounding box  
**Period requested:** 2026-10-01 to 2026-10-08  
**Minimum magnitude:** 4.5

### 7.1 API Connectivity

Both provider APIs successfully returned JSON earthquake records.

- USGS: 3 events
- EMSC: 4 events

These counts are not directly comparable until differences in query boundaries, catalog coverage, and filtering behavior have been investigated.

### 7.2 Schema Differences

USGS:
- Event identifier: `id`
- Occurrence timestamp: `properties.time`, Unix milliseconds
- Update timestamp: `properties.updated`, Unix milliseconds
- Magnitude: `properties.mag`
- Magnitude scale: `properties.magType`
- Depth: third geometry coordinate, positive in the inspected record

EMSC:
- Event identifier: `properties.unid`
- Occurrence timestamp: `properties.time`, ISO 8601
- Update timestamp: `properties.lastupdate`, ISO 8601
- Magnitude: `properties.mag`
- Magnitude scale: `properties.magtype`
- Depth: `properties.depth`, positive in the inspected record
- Third geometry coordinate: negative in the inspected record

### 7.3 Candidate Cross-Provider Match

USGS event: `us6000u0rx`  
EMSC event: `20261007_0000227`

Both providers reported an earthquake on October 7, 2026, at approximately 15:46:15 UTC.

Observed differences:

- Occurrence timestamps differ by approximately 0.233 seconds.
- Both report magnitude 4.7 mb.
- USGS depth: 107.82 km.
- EMSC depth: 109.3 km.
- Coordinates differ slightly.

The records are considered a strong candidate match, not yet a formally confirmed match.

### 7.4 Initial Engineering Findings

1. Provider-specific earthquake identifiers cannot be used directly as shared event identifiers.
2. Timestamp representations must be standardized to UTC.
3. Depth extraction must follow provider-specific field definitions.
4. Magnitude scales must be preserved alongside magnitude values.
5. Source observations should remain traceable after consolidation.
6. Geographic and temporal proximity may support event matching, but matching thresholds require further investigation.

### 7.5 Outstanding Questions

- Why did EMSC return an event occurring after the requested end-date boundary?
- Do both providers consistently preserve identifiers when event information changes?
- Which fields can legitimately be null?
- How should missing or conflicting magnitude scales be handled?
- What geographic and temporal tolerances are appropriate for matching?
- How should repeated observations and updated observations be stored?

These questions must be investigated before finalizing the canonical earthquake model.