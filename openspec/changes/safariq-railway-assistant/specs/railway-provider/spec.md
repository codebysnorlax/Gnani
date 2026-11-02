# Spec Delta: railway-provider

## Purpose
The `railway-provider` capability provides normalized railway schedule, running day, seat availability, and fare data through a pluggable provider interface with strict provenance tracking.

## ADDED Requirements

### Requirement: Normalized Railway Provider Interface
The system SHALL isolate all external railway data access behind a `RailwayProvider` interface that exposes declared capability flags and standard normalized models for stations, trains, schedules, availability, and fares.

#### Scenario: Provider returns normalized train search results
- **WHEN** a train search request is executed against a configured provider
- **THEN** the system receives normalized `TrainSearchResult` items containing train number, name, station codes, departure/arrival times, run days, and duration.

#### Scenario: Unsupported provider operation handled gracefully
- **WHEN** a provider capability flag indicates that live seat availability is not supported
- **THEN** the system returns an `UNSUPPORTED` availability status without making invalid API calls or fabricating availability numbers.

### Requirement: Service-Day Operating Validation
The system SHALL deterministically validate whether a candidate train operates on the requested journey boarding date using provider run-day schedule data before including it in matching results.

#### Scenario: Non-running train filtered out
- **WHEN** a train runs only on Mondays and Wednesdays, and the user's travel date is a Friday
- **THEN** the system marks the service day as invalid and excludes the train from the candidate options.

#### Scenario: Midnight-crossing overnight journey date offset
- **WHEN** a train departs at 22:30 on day T and arrives at 06:15 on day T+1
- **THEN** the system computes an arrival day offset of +1 and displays the arrival date as day T+1 in IST.

### Requirement: Availability Normalization and Freshness
The system SHALL normalize third-party availability status codes into a standard enum (`AVAILABLE_CONFIRMED`, `RAC`, `WAITLIST`, `NOT_AVAILABLE`, `REGRET_OR_CLOSED`, `UNKNOWN`, `UNSUPPORTED`) and attach provider name and retrieval timestamp.

#### Scenario: Waitlist preserved without confirmation guarantee
- **WHEN** provider returns a status indicating "WL 12"
- **THEN** the system maps the status to `WAITLIST`, preserves "WL 12" in `raw_status`, and never claims the seat will confirm.

#### Scenario: Stale availability flagged for refresh
- **WHEN** an availability snapshot is older than the configured freshness threshold (e.g., 120 seconds)
- **THEN** the system treats the snapshot as stale and triggers a fresh provider lookup when selected by the user.

### Requirement: Fare Arithmetic and Money Representation
The system SHALL represent all railway fares as integer paise and compute totals using exact `Decimal` arithmetic, preserving provider fare breakdown components when returned without inventing missing fees.

#### Scenario: Exact integer paise representation
- **WHEN** a provider quotes a fare of ₹1,845.50
- **THEN** the system stores the amount as 184550 paise and formats it as ₹1,845.50 only in user presentation layers.

#### Scenario: Estimated fare clearly labelled
- **WHEN** a provider returns an estimated or indicative fare quote
- **THEN** the system marks `quote_type` as `ESTIMATED` and labels the displayed fare as an estimate.

### Requirement: Strict Data Provenance and Demo Mode
The system SHALL attach `provider_id`, `retrieved_at`, and `is_demo` metadata to every retrieved dynamic railway fact, and visibly banner demo mock data to prevent presenting fixtures as live facts.

#### Scenario: Live provider provenance attached
- **WHEN** live train data is fetched from an active provider adapter
- **THEN** each train option record contains the provider identifier and ISO UTC retrieval timestamp.

#### Scenario: Mock provider activates demo banner
- **WHEN** `DEMO_MODE=true` is configured and mock provider fixtures are used
- **THEN** every result card and Telegram message carries a visible "DEMO DATA — NOT LIVE" indicator.
