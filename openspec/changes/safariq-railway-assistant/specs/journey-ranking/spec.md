# Spec Delta: journey-ranking

## Purpose
The `journey-ranking` capability applies deterministic filtering, JourneyFit multi-factor scoring, evidence-based reasoning, and What-If constraint simulations to candidate train options.

## ADDED Requirements

### Requirement: Hard Constraint Filtering
The system SHALL evaluate candidate trains against user-specified hard constraints (operating run day, origin/destination terminal match, class availability, budget ceiling, departure time window, and arrival deadline) prior to scoring.

#### Scenario: Train exceeding budget ceiling filtered
- **WHEN** user specifies a budget limit of ₹2,000 and a train fare is ₹2,450
- **THEN** the system filters out the train from the primary matching results.

#### Scenario: Train violating arrival deadline filtered
- **WHEN** user specifies an arrival deadline of before 09:00 and a train arrives at 10:15
- **THEN** the system excludes the train from the primary matching results.

#### Scenario: No trains satisfy all hard constraints
- **WHEN** no candidate trains satisfy every hard constraint
- **THEN** the system reports zero exact matches and offers controlled relaxation suggestions (e.g., adjust budget or departure window) without silently relaxing constraints.

### Requirement: Deterministic Multi-Factor JourneyFit Scoring
The system SHALL score candidate trains using a deterministic weighted algorithm combining price, journey duration, schedule window fit, availability status, and terminal preference without relying on an LLM for scoring calculations.

#### Scenario: Balanced profile scoring
- **WHEN** user requests train options without specific optimization flags
- **THEN** the system applies standard balanced weights (price 30%, duration 25%, timing fit 25%, availability 10%, terminal 10%) and assigns a composite score.

#### Scenario: Fastest train optimization
- **WHEN** user requests "Show the fastest train"
- **THEN** the system re-weights the candidates prioritizing shortest verified travel duration and presents the fastest option first.

### Requirement: Evidence-Based Recommendation Explanations
The system SHALL generate factual, verifiable explanations for why a train is ranked top based solely on verified provider attributes and constraints.

#### Scenario: Recommendation reason grounded in facts
- **WHEN** a train is ranked first under user constraints
- **THEN** the system explains that it was chosen because it arrives before 09:00, fits within the ₹2,500 budget, and has the shortest verified duration (7h 45m).

### Requirement: What-If Conversational Constraint Adjustment
The system SHALL allow users to modify individual travel constraints (such as departure window, travel class, or travel date) in subsequent messages while preserving all other active constraints.

#### Scenario: User modifies departure window only
- **WHEN** user says "Actually, I can only leave after 7 PM"
- **THEN** the system updates `depart_after` to "19:00", retains original origin, destination, date, class, and budget, and re-ranks matching trains.
