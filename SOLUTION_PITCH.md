# SAARTHI: Solution Pitch

Voice-First AI Pre-Litigation Legal Dossier Engine for Indian Consumers

---

## Executive Summary

SAARTHI (pronounced *saar-thee*) is a sovereign, voice-first pre-litigation legal assistant that transforms spoken consumer grievances in 10 Indic languages into formal, court-ready legal demand notices, National Consumer Helpline (NCH 1915) filings, and public escalation posts in under 4 minutes. Built on Gnani.ai Speech AI (Prisma v3.0 STT and Timbre v3.0 TTS) and deterministic legal calculation engines, SAARTHI bridges India's linguistic, literacy, and legal divide.

- Video Demonstration: https://lnkd.in/p/dHtHE5Na
- X (Twitter) Post: https://x.com/codebysnorlax/status/2119890661541544103
- Live Telegram Bot: https://t.me/SaarthiHQBot
- Source Code Repository: https://github.com/codebysnorlax/Gnani

---

## The Problem: India's 25,000 INR Consumer Abyss

Every day, millions of Indian consumers lose money to defective goods, delayed flight refunds, failed UPI transactions, and unfair trade practices. Over 95% of valid claims under 25,000 INR are abandoned due to three systemic bottlenecks:

1. Corporate Stonewalling: Customer service chatbots trap users in scripted rejection loops while concealing mandatory Nodal Grievance Officer contacts.
2. Linguistic and Regulatory Asymmetry: While grievances occur in vernacular languages, legal demand notices and Nodal Officer escalations require precise English legal terminology under the Consumer Protection Act, 2019 (CPA 2019).
3. Prohibitive Legal Costs: Hiring an advocate to draft a pre-litigation notice costs between 3,000 and 10,000 INR, making formal legal escalation economically irrational for micro- and mid-sized disputes.

---

## The Solution: Spoken Voice In, Court-Ready Dossier Out

SAARTHI allows any citizen to speak naturally in their mother tongue or code-mixed vernacular. It verifies missing facts through context-aware dialogue and deterministically synthesizes a comprehensive Tri-Fold Escalation Dossier:

1. Formal Legal Demand Notice (PDF): A court-ready A4 document citing exact statutory sections under CPA 2019, E-Commerce Rules 2020, RBI turnaround circulars, or the DGCA Passenger Charter, with precise integer-paise damage computations and Nodal Officer addresses.
2. NCH 1915 WhatsApp Filing: A structured grievance block with a one-tap deep link to the official National Consumer Helpline WhatsApp bot (+91 8860005372).
3. Public Social Escalation Post: A concise, impactful 280-character post tagging the brand's escalation handle and official regulatory watchdogs (@jagograhakjago, @DoCA_GoI).
4. Spoken Voice Guidance: A natural audio walkthrough delivered via Gnani Timbre TTS in the user's selected language explaining immediate next steps.

---

## Core Technical Innovations Powered by Gnani.ai

- Gnani Prisma v3.0 Speech-to-Text: High-accuracy transcription of emotional, colloquial, and code-mixed Indian speech with Inverse Text Normalization (ITN) and script-based Indic language detection.
- Gnani Timbre v3.0 Text-to-Speech: Natural voice responses across verified characters (Shivani, Devansh, Chetana) with strict sparse audio prosody tags (`<pauses>`, `<slow>`).
- Deterministic Statutory Core: Zero LLM hallucination in legal provisions. All statutes and integer-paise financial calculations are mapped deterministically via verified statutory registries.
- Client-Side Privacy: Automatic regex scrubbing of Aadhaar, PAN, and payment cards prior to processing, fully compliant with the Digital Personal Data Protection Act, 2023 (DPDP Act).
- Resilient Zero-Cost AI Architecture: 4-tier cascading model failover with local SQLite Write-Ahead Logging (WAL) ensuring complete offline durability.

---

## Impact & Value Proposition

Under Section 35 of the Consumer Protection Act, 2019, Indian citizens have the statutory right to represent themselves without an advocate. SAARTHI operationalizes this right by providing every citizen with an accessible, high-caliber legal drafting copilot in their pocket, democratizing access to justice across Bharat.
