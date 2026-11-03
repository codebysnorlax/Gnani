# Spec Delta

## Purpose

Ensures consumer privacy and compliance by deterministically redacting sensitive financial credentials and national identification numbers before persistence or external processing.

## ADDED Requirements

### Requirement: Pre-LLM PII scrubbing
The system SHALL execute deterministic regex sanitization on all raw user text and speech transcripts prior to database persistence or LLM invocation.

#### Scenario: 12-digit government identification sanitized
- **WHEN** incoming text contains an unformatted 12-digit sequence not prefixed by an order or transaction keyword
- **THEN** system replaces the sequence with [REDACTED_GOVT_ID]

#### Scenario: 16-digit payment card number sanitized
- **WHEN** incoming text contains a 16-digit payment card number with spaces or hyphens
- **THEN** system replaces the card number with [REDACTED_CARD]

#### Scenario: Confidential security tokens sanitized
- **WHEN** incoming text contains explicit PIN, CVV, or OTP references
- **THEN** system replaces secret codes with [REDACTED_SECRET]

### Requirement: Order and transaction reference preservation
The system SHALL preserve alphanumeric order numbers, PNRs, and bank UTRs without false redaction.

#### Scenario: Legitimate order identifier preserved
- **WHEN** incoming text contains an alphanumeric token such as OD3091823901 or a 12-digit UTR prefixed by UTR
- **THEN** system retains the token intact for legal notice drafting
