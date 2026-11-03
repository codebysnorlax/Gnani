# Spec Delta

## Purpose

Extracts structured dispute facts from multilingual consumer narratives across a resilient 4-tier cascading pipeline with offline fallback.

## ADDED Requirements

### Requirement: Multi-tier cascading grievance extraction
The system SHALL extract structured grievance facts by attempting extraction through a priority cascade: Tier 1 (Primary Cloud LLM), Tier 2 (Secondary Router), Tier 3 (Golden Demo Fixtures), and Tier 4 (Deterministic Regex & Keyword Engine).

#### Scenario: Primary LLM available
- **WHEN** consumer grievance text is provided and Tier 1 service responds successfully within timeout
- **THEN** system returns structured grievance schema populated from Tier 1 output

#### Scenario: Cloud LLMs fail or rate limit
- **WHEN** Tier 1 and Tier 2 encounter network failures, HTTP 429 rate limits, or timeout
- **THEN** system automatically falls back to Tier 3 or Tier 4 without raising an unhandled exception

#### Scenario: Golden demo phrase matched
- **WHEN** input matches a registered demo fixture key or hash in demonstration mode
- **THEN** system returns verified pre-computed grievance schema within 50 milliseconds

### Requirement: Relative date normalization
The system SHALL convert relative date expressions in Hindi, Hinglish, or English into absolute calendar dates (YYYY-MM-DD) based on current Indian Standard Time (IST).

#### Scenario: Relative colloquial date in grievance
- **WHEN** consumer states relative dates such as "kal", "yesterday", or "parso"
- **THEN** system converts the expression to the exact ISO date relative to current IST date

#### Scenario: Explicit calendar date
- **WHEN** consumer mentions an explicit date such as "25 Oct" or "12-10-2026"
- **THEN** system formats the date into canonical YYYY-MM-DD representation

### Requirement: Objective English incident summarization
The system SHALL produce a concise, formal 2-to-3 sentence English factual summary from consumer statements provided in Hindi, Hinglish, or English.

#### Scenario: Hindi narrative input
- **WHEN** consumer submits an informal Hindi grievance describing defective goods
- **THEN** system translates and refines the narrative into an objective legal statement of facts in English

### Requirement: Order and transaction identifier extraction
The system SHALL extract alphanumeric transaction, order, UTR, or PNR identifiers only when explicitly present in the input text, setting the field to null otherwise.

#### Scenario: Explicit order identifier present
- **WHEN** consumer narrative contains an order reference like "OD123456789" or "UTR987654"
- **THEN** system extracts the identifier without punctuation contamination

#### Scenario: No order identifier present
- **WHEN** consumer explains a dispute without providing any reference code
- **THEN** system sets order identifier to null and marks it as a pending clarification field
