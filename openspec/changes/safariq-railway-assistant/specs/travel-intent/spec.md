# Spec Delta: travel-intent

## Purpose
The `travel-intent` capability parses natural language travel requests from text and speech into structured travel constraints, resolves ambiguous dates and stations against real reference data, and prompts for missing criteria.

## ADDED Requirements

### Requirement: Natural Language Travel Intent Parsing
The system SHALL parse unstructured user text into a strictly typed travel intent model with fields for origin, destination, journey date, passenger count, preferred class, quota, budget ceiling, departure time bounds, and arrival deadline.

#### Scenario: Complete travel intent extracted
- **WHEN** a user submits "Bokaro to Delhi on 15 Nov, 3AC, 1 passenger, budget under 2500, arrive before 9 AM"
- **THEN** the system parses origin as "Bokaro", destination as "Delhi", journey date as "2026-11-15", travel class as "3A", quota as "GN", passenger count as 1, max budget as 250000 paise, and arrival deadline as "09:00".

#### Scenario: Incomplete travel intent requests clarification
- **WHEN** a user submits "I want to go to Delhi tomorrow" without specifying origin station
- **THEN** the system sets origin as null, marks "origin" in missing fields, and prompts the user with a focused clarification question.

### Requirement: Voice Request Transcription via Gnani Prisma
The system SHALL accept Telegram voice notes and audio clips under 30 seconds and transcribe them using the Gnani Prisma v3 REST API (`https://api.vachana.ai/stt/v3`), falling back gracefully to text input if credentials or services are unavailable.

#### Scenario: Successful voice transcription in Hindi/Hinglish
- **WHEN** a user sends an audio note speaking "Mujhe 15 November ko Bokaro se Delhi jaana hai"
- **THEN** the system calls Gnani Prisma v3 STT, extracts the transcript, echoes the recognized text to the user, and routes the transcript to the intent parser.

#### Scenario: Gnani API failure fallback
- **WHEN** Gnani STT returns HTTP 401, 403, 429, or network error
- **THEN** the system catches the exception, does not retry blindly or guess a transcript, and sends a user-safe message prompting them to type their journey request.

### Requirement: India Standard Time (Asia/Kolkata) Date Resolution
The system SHALL resolve relative and yearless dates using `Asia/Kolkata` local time, converting them into explicit ISO dates (`YYYY-MM-DD`), rejecting past dates, and echoing the absolute date with year to the user.

#### Scenario: Yearless date resolved to nearest future date
- **WHEN** a user requests travel on "15 November" while current IST date is 2 November 2026
- **THEN** the system resolves the journey date to "2026-11-15" in `Asia/Kolkata` and displays "15 November 2026" to the user.

#### Scenario: Past date rejected
- **WHEN** a user requests a journey date that precedes the current date in `Asia/Kolkata`
- **THEN** the system rejects the input with an explanation and asks the user to provide a valid upcoming travel date.

### Requirement: Station Candidate Matching and Disambiguation
The system SHALL normalize and match user station queries against a verified railway station master directory, returning candidate station codes and requiring explicit user selection whenever multiple terminals or ambiguous matches exist.

#### Scenario: Single high-confidence station resolved
- **WHEN** a user specifies "Bokaro Steel City"
- **THEN** the system matches station code "BKSC", canonical name "Bokaro Steel City", and presents it in the search confirmation.

#### Scenario: Ambiguous city with multiple terminals prompts selection
- **WHEN** a user specifies "Delhi" as destination
- **THEN** the system identifies candidate stations (e.g., NDLS, DLI, NZM, ANVT), presents them as interactive inline buttons, and does not execute a train search until a selection is confirmed.

#### Scenario: Unrecognized station query
- **WHEN** a user enters an unrecognized station name that cannot be matched within confidence thresholds
- **THEN** the system does not hallucinate a station code, reports that the station was not found, and asks the user to check the spelling or provide the 3-4 letter station code.
