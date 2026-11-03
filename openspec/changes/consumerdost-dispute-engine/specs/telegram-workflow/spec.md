# Spec Delta

## Purpose

Coordinates conversational dispute intake, slot clarification loops, interactive case confirmation, document delivery, and user privacy controls over Telegram.

## ADDED Requirements

### Requirement: Conversational intake and slot filling
The system SHALL ingest voice notes and text messages, identifying missing mandatory facts (Complainant Full Name, Brand Name, Order ID, Amount Paid, Incident Date) and requesting missing information in concise follow-up prompts.

#### Scenario: Missing required fact
- **WHEN** consumer grievance narrative omits the paid amount or order identifier
- **THEN** system prompts the user specifically for the missing item without repeating already established facts

#### Scenario: All mandatory facts present
- **WHEN** consumer provides all required dispute facts in initial voice note or subsequent turns
- **THEN** system advances workflow directly to statutory evaluation and case confirmation

### Requirement: Interactive case confirmation card
The system SHALL present a structured summary of extracted facts, legal grounds, and total calculated claim with inline action buttons to confirm or edit details prior to document generation.

#### Scenario: Case presentation
- **WHEN** all dispute slots are resolved
- **THEN** system sends an inline card displaying case facts, statutory sections, financial totals, and buttons to generate notice or edit fields

### Requirement: Idempotent message processing and persistence
The system SHALL maintain conversational state across sessions using an asynchronous database with Write-Ahead Logging and discard duplicate Telegram updates.

#### Scenario: Telegram duplicate update delivery
- **WHEN** Telegram retries an identical update ID
- **THEN** system ignores duplicate invocation and maintains state consistency

### Requirement: User privacy and data deletion commands
The system SHALL provide a `/privacy` command allowing consumers to immediately delete all personal records, cached documents, and state sessions from the system.

#### Scenario: User issues privacy purge command
- **WHEN** user sends `/privacy` command
- **THEN** system deletes all grievance history, generated notices, and active session state associated with the user ID and confirms completion
