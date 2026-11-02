# Spec Delta: booking-handoff

## Purpose
The `booking-handoff` capability provides safe pre-booking revalidation, fare/seat drift detection, copyable search summaries, and official IRCTC website handoffs without booking tickets or collecting payment credentials.

## ADDED Requirements

### Requirement: Pre-Handoff Revalidation and Drift Detection
The system SHALL re-query the provider for fresh fare and seat availability when a user selects a train option for booking, comparing the refreshed quote to the previously displayed quote.

#### Scenario: Fare or availability changes before handoff
- **WHEN** refreshed fare increases from ₹1,850 to ₹2,150 or status changes from Available to RAC
- **THEN** the system displays the difference to the user and requires explicit acknowledgement before proceeding to handoff.

#### Scenario: Selected train becomes unavailable
- **WHEN** the refreshed lookup indicates that the train is fully booked or no longer verifiable
- **THEN** the system informs the user and offers a fresh search rather than generating a stale handoff summary.

### Requirement: Copyable Booking Summary Preparation
The system SHALL format an unambiguous, copyable plain-text summary containing train number, train name, travel date, boarding and destination station codes, class code, quota, passenger count, and last retrieved fare with timestamp.

#### Scenario: User receives copyable summary
- **WHEN** a user confirms handoff preparation for a validated train
- **THEN** the system outputs a formatted text block ready for copy-pasting into the official booking platform.

### Requirement: Allowlisted Official Portal Redirection
The system SHALL provide a redirect link strictly pointing to the allowlisted official IRCTC portal (`https://www.irctc.co.in/nget`) and SHALL NOT accept arbitrary external URLs.

#### Scenario: Official link opened
- **WHEN** user clicks "Book on official IRCTC" button
- **THEN** the system opens the configured allowlisted IRCTC URL with clear instructions to log in and complete booking on that platform.

### Requirement: Prohibition of Booking Claims and Credential Collection
The system SHALL NOT collect IRCTC login passwords, OTPs, or payment details, and SHALL NOT emit messages claiming a ticket has been booked or a PNR generated.

#### Scenario: Booking handoff disclaimer displayed
- **WHEN** handoff summary is presented to the user
- **THEN** the message explicitly states that SAFARIQ has prepared the journey details and that the ticket is not yet booked.
