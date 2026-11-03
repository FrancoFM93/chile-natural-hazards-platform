# Project Foundation

## Project

Chile Natural Hazards Intelligence Platform

## Overview

The Chile Natural Hazards Intelligence Platform is a cloud-native data platform designed to ingest, standardize, validate, preserve, enrich, and expose analytics-ready information about natural hazards affecting Chile.

The platform will use Microsoft Fabric and Azure services where they provide a clear engineering benefit.

The platform itself is the product. Power BI will be one consumer of processed data, not the center of the architecture.

## Business Context

Natural-hazard information relevant to Chile is distributed across multiple national and international providers.

These providers may describe the same event using different schemas, identifiers, timestamps, geographic references, severity measurements, update frequencies, and publication mechanisms.

This fragmentation makes it difficult to build reliable analytical systems directly on top of individual source formats.

A monitoring organization, infrastructure company, mining company, insurance company, university, or public-sector analytical team could benefit from a common data foundation that consolidates and standardizes this information.

## Problem Statement

Organizations analyzing natural hazards affecting Chile need a reliable way to integrate data from heterogeneous providers without coupling downstream analytical systems to each provider's schema.

The platform must preserve source-level information while transforming provider-specific observations into consistent, traceable, and analytics-ready event data.

## Initial Scope

Version 1 will focus exclusively on earthquakes affecting Chile.

The first supported data source will be the USGS Earthquake API.

The architecture should allow additional earthquake providers and other natural-hazard sources to be incorporated later without redesigning the core platform.

Future event types may include:

- Wildfires
- Volcanoes
- Tsunamis
- Weather alerts
- Air quality events

These future event types are architectural considerations only and are not part of the Version 1 implementation scope.

## Functional Requirements

### FR-01: Ingest earthquake data

The platform must ingest earthquake records from the USGS Earthquake API for events relevant to Chile.

### FR-02: Preserve source data

The platform must preserve the original provider data or a lossless representation of it before transformation.

### FR-03: Standardize provider data

The platform must transform provider-specific earthquake records into a consistent internal representation.

### FR-04: Identify event updates

The platform must distinguish between newly observed earthquake records and updates to previously observed provider events.

### FR-05: Prevent uncontrolled duplication

Repeated ingestion of the same provider record must not create uncontrolled duplicate analytical records.

### FR-06: Validate incoming data

The platform must validate incoming records for required fields, valid timestamps, geographic coordinates, identifiers, and other relevant quality rules.

### FR-07: Isolate invalid records

Records that fail critical data-quality checks must be identifiable and separated from trusted analytical datasets without being silently discarded.

### FR-08: Enrich earthquake events with Chilean geographic context

The platform must derive useful geographic context from event coordinates where possible, such as Chilean region and whether the event occurred inland or offshore.

### FR-09: Maintain source traceability

Processed records must retain enough metadata to trace them back to the original provider and provider event identifier.

### FR-10: Provide analytics-ready data

The platform must expose curated earthquake data in a structure suitable for SQL analysis and downstream analytical consumers.

### FR-11: Support historical analysis

The platform must retain enough historical information to analyze earthquake activity and changes to provider-reported events over time.

### FR-12: Expose platform health information

The platform must provide information about ingestion freshness, record volumes, processing failures, and data-quality outcomes.

### FR-13: Support future providers

The platform design must allow additional earthquake providers to be incorporated without requiring major redesign of downstream analytical models.


## Non-Functional Requirements

### NFR-01: Maintainability

The platform should use clear module boundaries, documented interfaces, and simple implementation patterns so that a junior engineer can understand, modify, and extend the system.

### NFR-02: Extensibility

Provider-specific ingestion logic must be isolated from downstream transformation and analytical logic.

Adding a new earthquake provider should require implementing a new provider-specific adapter without redesigning the core event model.

### NFR-03: Data Traceability

Curated records must retain sufficient metadata to identify their source provider, source event identifier, ingestion timestamp, and relevant processing information.

### NFR-04: Idempotency

Reprocessing the same source records must not create duplicate trusted analytical records.

### NFR-05: Data Quality Visibility

Data-quality failures must be measurable and observable.

The platform should expose counts or metrics for accepted, rejected, duplicated, and failed records where practical.

### NFR-06: Near-Real-Time Availability

New or updated earthquake information should normally become available to downstream analytical consumers within five minutes of being detected by the ingestion process.

This is a target for the portfolio implementation rather than a formal production service-level agreement.

### NFR-07: Recoverability

The platform should preserve enough source data and processing metadata to allow failed transformations to be rerun without requiring the original provider to resend the data.

### NFR-08: Cost Awareness

The architecture should favor low-cost or consumption-based services appropriate for the expected portfolio workload.

Expensive infrastructure should not be introduced solely to demonstrate a technology.

### NFR-09: Observability

The platform should provide basic visibility into ingestion activity, failures, processing outcomes, and data freshness.

### NFR-10: Testability

Core transformation, validation, matching, and provider-handling logic should be testable independently from cloud infrastructure where practical.

### NFR-11: Security

Secrets and credentials must not be committed to the repository.

Access to cloud resources should follow least-privilege principles where practical for the portfolio environment.

### NFR-12: Documentation

Major architectural decisions, data models, transformation rules, and operational procedures must be documented alongside the implementation.

### NFR-13: Reproducibility

Another developer should be able to understand the required environment and reproduce the core project workflow using the repository documentation.


## Assumptions

### A-01: Public data availability

Version 1 assumes that the USGS Earthquake API remains publicly accessible and sufficiently stable for the purposes of the project.

### A-02: Portfolio-scale workload

The expected event volume is small compared with a production-scale streaming platform.

The architecture should demonstrate appropriate engineering patterns without pretending that the project processes enterprise-scale traffic.

### A-03: Analytical use

The platform is intended for analytical and educational purposes. It is not an authoritative source for emergency response or public safety decisions.

### A-04: Geographic focus

Version 1 focuses on earthquake events relevant to Chile. The exact geographic relevance rules will be defined during source and data-model analysis.

### A-05: Future sources

Additional providers and hazard types are expected to have different schemas and semantics. The architecture should accommodate this possibility without implementing those integrations in Version 1.


## Constraints

### C-01: Junior portfolio scope

The project must remain understandable, maintainable, and defensible by a Junior Data Engineer candidate.

Architectural complexity must be justified by a concrete engineering or learning benefit.

### C-02: Cost

The project should remain inexpensive to operate after development and experimentation.

Temporary Azure credits may be used for learning and architectural experiments, but the permanent architecture should not depend on unnecessarily expensive infrastructure.

### C-03: Microsoft ecosystem

Microsoft Fabric and Azure are the primary cloud technologies for the project.

This does not require using Microsoft services when they do not improve the solution.

### C-04: Public data sources

The project should rely primarily on publicly accessible data that can legally and practically be used for portfolio purposes.

### C-05: Development resources

The platform is developed and maintained by one developer, with AI-assisted development tools used to accelerate implementation, testing, and documentation.


## Risks

### R-01: Source availability

External APIs may become unavailable, change their schemas, introduce rate limits, or modify their access policies.

### R-02: Overengineering

The desire to demonstrate multiple Microsoft technologies could introduce services that are unnecessary for the actual workload.

Architecture decisions must therefore be justified independently of portfolio visibility.

### R-03: Scope expansion

Supporting additional natural hazards could significantly increase data-model and ingestion complexity.

Version 1 must remain focused on earthquakes.

### R-04: Provider inconsistency

Different providers may report different values for the same real-world earthquake.

Future multi-provider support must preserve source observations rather than silently treating conflicting values as identical.

### R-05: Geographic ambiguity

Offshore and border events may not map cleanly to Chilean administrative regions.

The platform must represent geographic uncertainty rather than forcing every event into a region.

### R-06: Cloud dependency

Some parts of the platform may depend on paid or trial cloud services.

Core transformation and validation logic should remain testable outside cloud infrastructure where practical.


## Success Criteria

Version 1 will be considered successful when:

1. Earthquake data relevant to Chile can be ingested automatically from USGS.
2. Original source data is preserved for traceability and reprocessing.
3. Provider records are transformed into a documented internal event representation.
4. Repeated processing does not create uncontrolled duplicate analytical records.
5. Invalid or suspicious records can be identified without being silently discarded.
6. Earthquake records are enriched with useful Chilean geographic context where possible.
7. Curated data can be queried using SQL.
8. Historical earthquake activity can be analyzed using an analytical data model.
9. Power BI can consume the curated analytical data without depending directly on the USGS schema.
10. Basic pipeline freshness, processing outcomes, and data-quality information are observable.
11. Core transformation and validation logic is covered by automated tests.
12. Major architectural decisions and tradeoffs are documented.
13. The project can be explained and demonstrated end to end by its developer.


## Out of Scope for Version 1

Version 1 will not include:

- Earthquake prediction
- Machine learning
- Automated emergency notifications
- SMS or push notifications
- Official emergency alerts
- Disaster-response recommendations
- Public safety decision support
- Wildfire ingestion
- Volcano ingestion
- Tsunami ingestion
- Weather-alert ingestion
- Air-quality ingestion
- Mobile applications
- Public-facing APIs
- Complex geospatial modeling
- Multi-cloud architecture
- Kubernetes
- Enterprise-scale high-availability guarantees

Additional earthquake providers may be investigated and prototyped, but productionizing multiple providers is not required for Version 1.
