# Spec Delta

## Purpose

Enables voice-driven consumer dispute reporting by ingesting audio messages via Telegram and integrating with the Gnani AI Speech APIs for Indic speech-to-text and text-to-speech.

## ADDED Requirements

### Requirement: Audio message intake and size validation
The system SHALL accept voice notes and audio clips in OGG, OGA, MP3, or WAV format with duration up to 60 seconds and file size up to 20 megabytes.

#### Scenario: Valid audio clip accepted
- **WHEN** user uploads a 30-second voice note on Telegram
- **THEN** system downloads the audio file securely and prepares it for speech transcription

#### Scenario: Audio clip duration exceeded
- **WHEN** user uploads an audio recording exceeding 60 seconds
- **THEN** system rejects the audio file with a message requesting a shorter note or text input

### Requirement: Speech transcription via Gnani Prisma v3
The system SHALL transcribe audio into text using Gnani Prisma v3.0 REST STT with automatic Indic language detection and Inverse Text Normalization.

#### Scenario: Hindi voice grievance transcribed
- **WHEN** user submits a voice note spoken in colloquial Hindi or Hinglish
- **THEN** system receives normalized text with transcribed dates and currency amounts

#### Scenario: STT API timeout or failure fallback
- **WHEN** Gnani STT API fails, returns HTTP 4xx/5xx, or times out after 5.0 seconds
- **THEN** system gracefully switches the conversation turn to text prompt mode without losing context

### Requirement: Voice summary generation via Gnani Timbre
The system SHALL generate a 15-to-20 second audio summary using Gnani Timbre REST TTS explaining pre-litigation action steps in Hindi or English.

#### Scenario: Audio wrap-up generated successfully
- **WHEN** legal escalation bundle generation completes
- **THEN** system delivers an audio message summarizing next steps to the user

#### Scenario: TTS generation failure resilience
- **WHEN** Gnani TTS API is unavailable or times out
- **THEN** system skips voice note delivery while delivering all text and PDF artifacts without failure
