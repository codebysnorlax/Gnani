# Spec Delta

## Purpose

Maps consumer disputes to Indian statutory protections and calculates deterministic financial damages, interest, and penalties in integer paise.

## ADDED Requirements

### Requirement: Statutory provision mapping
The system SHALL map consumer grievance categories and issue types to corresponding legal provisions under the Consumer Protection Act, 2019, E-Commerce Rules 2020, CCPA Guidelines, or sectoral regulator mandates.

#### Scenario: Defective e-commerce goods
- **WHEN** consumer grievance involves defective goods and refused returns on e-commerce platforms
- **THEN** system maps the claim to CPA 2019 Section 2(10) (defect), Section 2(47) (unfair trade practice), and Consumer Protection (E-Commerce) Rules, 2020

#### Scenario: Failed UPI transaction debit
- **WHEN** consumer grievance involves an uncredited UPI debit exceeding turnaround time
- **THEN** system maps the claim to RBI Circular on Harmonisation of Turn Around Time (TAT) and customer compensation

### Requirement: Deterministic integer-paise financial calculations
The system SHALL calculate all monetary claims, statutory interest, and compensatory damages strictly in integer paise to prevent floating-point rounding errors.

#### Scenario: Equitable statutory interest calculation
- **WHEN** refund has been withheld beyond the incident date
- **THEN** system calculates 9 percent per annum simple equitable interest on the principal amount in paise from incident date to notice date

#### Scenario: Tiered compensation for harassment and mental agony
- **WHEN** dispute damage assessment is computed
- **THEN** system applies deterministic tiered compensation for harassment and mental agony bounded by proportional claim caps

### Requirement: Statutory cure period specification
The system SHALL compute and state a formal 15-calendar-day statutory cure period in all demand notices prior to initiating District Consumer Commission proceedings.

#### Scenario: 15-day cure notice deadline
- **WHEN** a legal demand notice is compiled
- **THEN** notice explicitly states that the counterparty has 15 calendar days from receipt to remedy the default before escalation under Section 35 of CPA 2019
