# Spec Delta

## Purpose

Generates professional pre-litigation escalation deliverables including formal Legal Notice PDF, National Consumer Helpline filing block, and executive social escalation text.

## ADDED Requirements

### Requirement: Unicode-safe legal demand notice PDF generation
The system SHALL generate an A4 formal Legal Demand Notice in PDF format with embedded TrueType fonts ensuring complete rendering of Indian Rupee currency symbols and special characters without character substitution boxes.

#### Scenario: PDF compilation with Rupee symbol
- **WHEN** consumer requests final escalation package
- **THEN** system produces a downloadable PDF notice containing correctly rendered INR currency symbols, statutory citations, financial table, and Section 35 CPA self-representation signature block

#### Scenario: Multi-page document pagination
- **WHEN** narrative details span across multiple pages
- **THEN** system applies running headers, page numbers ("Page X of Y"), and legal verification footers cleanly

### Requirement: National Consumer Helpline 1915 dossier generation
The system SHALL compile a pre-formatted National Consumer Helpline (NCH 1915 / INGRAM) grievance submission block with a one-click WhatsApp pre-filled filing link.

#### Scenario: NCH filing block export
- **WHEN** case dossier is generated
- **THEN** system outputs a structured text block containing brand name, category, order reference, grievance summary, and a pre-composed WhatsApp deep link to 1915

### Requirement: Public accountability social escalation draft
The system SHALL generate an objective, legally grounded social media escalation post formatted within 280 characters including the verified company handle, order ID, and regulatory tags.

#### Scenario: Social post generation
- **WHEN** escalation package is requested
- **THEN** system crafts a factual, non-defamatory post citing the brand handle, incident ID, CPA 2019 reference, and relevant regulatory handles
