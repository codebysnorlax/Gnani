# Spec Delta

## Purpose

Resolves colloquial company mentions to canonical corporate entities, registered legal addresses, statutory nodal emails, and verified social handles.

## ADDED Requirements

### Requirement: Canonical brand entity resolution
The system SHALL resolve raw brand mentions and colloquial aliases against a curated directory of Indian corporate entities using fuzzy token matching.

#### Scenario: Exact brand alias match
- **WHEN** consumer mentions a known alias such as "fk" or "flipkart india"
- **THEN** system resolves the brand to canonical entity "FLIPKART" with full corporate record

#### Scenario: Minor misspelling or transliterated brand
- **WHEN** consumer enters a misspelled company name exceeding 80% fuzzy similarity threshold
- **THEN** system resolves the entity to the closest matching directory brand

### Requirement: Unlisted brand fallback handling
The system SHALL support grievance processing for brands not present in the master corporate directory by capturing custom brand names and requesting or generating placeholder grievance contacts.

#### Scenario: Brand absent from directory
- **WHEN** consumer files a complaint against a local or unlisted merchant
- **THEN** system accepts the raw brand name and prompts the user for nodal contact details or applies standard statutory escalation defaults

### Requirement: Statutory contact metadata retrieval
The system SHALL provide registered office address, nodal grievance officer title, nodal email, and official social media handles for resolved brands.

#### Scenario: Resolved brand metadata lookup
- **WHEN** brand is successfully matched in the corporate directory
- **THEN** system retrieves corporate legal name, registered physical address, official nodal email, and social handle for notice generation
