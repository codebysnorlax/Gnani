# Spec Delta: telegram-agent

## Purpose
The `telegram-agent` capability orchestrates the conversational Telegram bot interface, manages LangGraph state workflows with SQLite checkpoints, and guarantees update processing idempotency.

## ADDED Requirements

### Requirement: Telegram Command and Conversational Lifecycle
The system SHALL support standard commands (`/start`, `/help`, `/plan`, `/cancel`, `/privacy`) and accept free-form conversational text and voice messages in private Telegram chats.

#### Scenario: User starts bot with /start
- **WHEN** a user sends `/start`
- **THEN** the system creates or activates the user record, displays welcome guidance explaining capabilities and privacy rules, and notes that it does not book tickets.

#### Scenario: User cancels active flow with /cancel
- **WHEN** a user sends `/cancel` during a multi-turn clarification or search workflow
- **THEN** the system cancels the active state graph, clears pending interrupts, and confirms that the session was reset.

### Requirement: Telegram Update Idempotency
The system SHALL record incoming Telegram update IDs in a persistent `processed_updates` table and reject duplicate incoming updates without re-executing search or database mutations.

#### Scenario: Duplicate Telegram update received
- **WHEN** Telegram retries an update with an `update_id` already recorded in `processed_updates`
- **THEN** the system ignores the duplicate update and does not re-run graph steps or send duplicate responses.

### Requirement: Interactive Inline Keyboards and Callback Validation
The system SHALL use Telegram inline keyboards for option selections, confirmation, and pagination, keeping `callback_data` payloads under 64 bytes and calling `answerCallbackQuery` promptly.

#### Scenario: Callback query answered within Telegram constraints
- **WHEN** a user clicks an inline button on a train option card
- **THEN** the system immediately answers the callback query to dismiss the loading indicator and routes the opaque callback token to resume the active LangGraph workflow.

### Requirement: LangGraph Workflow State and SQLite Persistence
The system SHALL persist conversational trip sessions, search results, and agent checkpoints in SQLite using `aiosqlite` and `langgraph-checkpoint-sqlite` across application restarts.

#### Scenario: Workflow resumes after service restart
- **WHEN** the application restarts while a user is awaiting station clarification
- **THEN** the user's next message resumes the saved checkpoint from SQLite using the user and thread identifier without losing context.
