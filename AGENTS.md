# AGENTS.md

# Financial Transaction Intelligence Engine

## Project Vision

This project is a hybrid deterministic + AI-assisted financial transaction intelligence engine built for BFSI (Banking, Financial Services, and Insurance) workflows.

The goal is NOT merely to categorize transactions using keywords.

The goal is to build a robust semantic financial intelligence system capable of:

- Understanding banking transaction protocols
- Parsing structured financial narration formats
- Extracting semantic meaning from financial metadata
- Detecting transaction intent and transaction families
- Handling noisy real-world banking narrations
- Producing explainable classifications
- Modeling uncertainty and ambiguity
- Scaling across banks, protocols, rails, and transaction types
- Supporting AI-assisted validation and reasoning

The architecture intentionally avoids relying entirely on LLMs.

Instead:

- deterministic semantic intelligence performs the heavy lifting
- AI acts as a validation and reasoning layer

This dramatically improves:

- reliability
- explainability
- cost efficiency
- consistency
- auditability
- maintainability

---

# Core Philosophy

## Deterministic First

The deterministic engine is the foundation.

AI should NEVER be the primary classifier.

AI should:

- validate
- refine
- explain
- resolve ambiguity
- handle edge cases

The deterministic layer should:

- parse
- extract
- infer
- structure
- enrich
- model confidence

This architecture is intentional.

---

# Current System Architecture

```text
Raw Transaction Narration
            ↓
Normalization Layer
            ↓
Protocol Detection
            ↓
Protocol-Aware Parsing
            ↓
Semantic Signal Extraction
            ↓
Entity Intelligence Layer
            ↓
Conflict Detection
            ↓
Confidence Modeling
            ↓
Deterministic Classification
            ↓
AI Validation Layer (future)
            ↓
Final Classification
```

---

# Current Project Structure

```text
engine/
│
├── classifier.py
├── confidence.py
├── entity_intelligence.py
├── loader.py
├── normalizer.py
├── parser.py
├── pipeline.py
├── rules.py
├── signals.py
│
├── rules/
│   ├── category_rules.json
│   ├── merchant_rules.json
│   └── mode_rules.json
│
└── future/
    ├── ai_validator.py
    ├── protocol_registry.py
    ├── ontology.py
    └── semantic_memory.py
```

---

# Current Capabilities

## 1. Normalization Layer

Responsible for:

- uppercasing narrations
- removing noise
- standardizing separators
- improving parser consistency

Example:

```text
upi/12345/p2m/amazon@apl
```

becomes:

```text
UPI/12345/P2M/AMAZON@APL
```

---

# 2. Protocol Detection

Current supported rails:

- UPI
- IMPS
- NEFT
- RTGS
- ATM
- CHEQUE

The engine detects which financial rail a transaction belongs to before parsing.

This is critical because each rail has different narration structures.

---

# 3. Protocol-Aware Parsing

This is one of the most important architectural layers.

The engine no longer assumes all narrations follow the same format.

Instead:

- protocol families are identified
- parsing logic changes dynamically

Example:

## UPIAR Example

```text
UPIAR/409247144861/DR/PRUSHOTA/SBIN
```

Parsed as:

| Field | Value |
|---|---|
| Prefix | UPIAR |
| Reference ID | 409247144861 |
| Subtype | DR |
| Entity | PRUSHOTA |
| Bank | SBIN |

---

# 4. Semantic Signal Layer

The signal system extracts binary semantic indicators.

Examples:

- reversal_flag
- bounce_flag
- charge_flag
- salary_flag
- tax_flag
- utility_flag
- loan_flag
- recharge_flag
- travel_flag
- investment_flag

Signals are intentionally lightweight.

Signals are NOT final classifications.

They are semantic evidence.

---

# IMPORTANT SIGNAL DESIGN PRINCIPLE

Signals must use token-safe matching.

Substring matching is dangerous.

BAD:

```python
if "REV" in narration
```

This incorrectly matches:

```text
FOREVER
```

The system now uses boundary-aware regex matching.

GOOD:

```python
r'\bREV\b'
```

This significantly improves semantic precision.

---

# 5. Conflict Detection Layer

The system models ambiguity explicitly.

Examples:

| Conflict | Meaning |
|---|---|
| deposit_withdrawal_conflict | contradictory semantics |
| cash_cheque_conflict | overlapping categories |
| weak_signal_match | low semantic confidence |

Conflicts reduce classification confidence.

This is intentional.

---

# 6. Confidence Layer

Every classification produces:

- category
- confidence
- decision path
- conflicts
- matched rule

Example:

```json
{
  "category": "TRANSFER OUT",
  "confidence": 0.65,
  "decision_path": [
    "protocol_subtype_p2v",
    "direction_out"
  ],
  "conflicts": []
}
```

The confidence layer is deterministic.

It is NOT AI-generated.

---

# 7. Entity Intelligence Layer

The engine performs semantic enrichment using entity recognition.

Example:

| Entity | Semantic Meaning |
|---|---|
| IRCTC | TRAVEL |
| LIC | INSURANCE |
| AMAZON | E-COMMERCE |
| AIRTEL | RECHARGE |

This is much stronger than narration keyword matching.

---

# 8. Subtype Intelligence

Transaction subtypes are treated as semantic protocol indicators.

Examples:

| Subtype | Meaning |
|---|---|
| P2M | Merchant Payment |
| P2V | Peer Transfer |
| REV | Reversal |
| DR | Debit |
| CR | Credit |

This is evolving into a transaction ontology layer.

---

# Current Supported Categories

```text
ACH BOUNCED CHARGES
SALARY RECEIVED
CHEQUE DEPOSIT
FUEL
INTEREST
LOAN
ELECTRONIC FUND TRANSFER
CASH WITHDRAWAL
FIXED DEPOSIT
IMPS BOUNCE CHARGES
NEFT BOUNCE
CHEQUE BOUNCE - TECHNICAL
SALARY
ECS BOUNCED CHARGES
ATM WITHDRAWAL
REFUND OR REVERSAL
IMPS BOUNCE
TAX
TRANSFER OUT
ATM DEPOSIT
CREDIT CARD PAYMENT
RTGS BOUNCE
DEBIT CARD TRANSFER IN
E-COMMERCE
RECHARGE
CHEQUE BOUNCE - NON TECHNICAL
DEMAND DRAFT
SALARY PAID
CHEQUE WITHDRAWAL
TRANSFER IN
CASH DEPOSIT
BANK CHARGES
AUTO SWEEP
INSURANCE
TRAVEL
DEBIT CARD TRANSFER OUT
PAYMENT GATEWAY
CHEQUE CASH WITHDRAWAL
UTILITY
INVESTMENTS
```

---

# Current Architectural Priorities

## HIGH PRIORITY

### 1. Parser Expansion

Need support for:

- additional UPI families
- bank-specific narration formats
- NEFT variants
- IMPS variants
- RTGS variants
- ECS formats
- ACH formats
- cheque structures
- debit card formats

The parser layer is currently the highest leverage improvement area.

---

### 2. Entity Intelligence Expansion

The entity registry currently has limited coverage.

Need:

- merchant dictionaries
- semantic entity grouping
- merchant category mapping
- fuzzy merchant normalization
- brand aliases
- multilingual handling

Example:

```text
AMZN
AMAZON
AMAZON PAY
```

should normalize to:

```text
AMAZON
```

---

### 3. Transaction Ontology

Need a formal semantic ontology.

Examples:

| Protocol Token | Semantic Meaning |
|---|---|
| P2M | Merchant Payment |
| P2V | Peer Transfer |
| REV | Reversal |
| EMI | Loan Payment |
| ECS | Auto Debit |

The ontology layer should eventually drive semantic interpretation.

---

### 4. Rail-Specific Intelligence

The engine currently understands rails at a moderate level.

Need:

- UPI-specific intelligence
- IMPS-specific intelligence
- NEFT-specific intelligence
- RTGS-specific intelligence
- ATM-specific intelligence
- cheque lifecycle intelligence

---

### 5. Advanced Conflict Modeling

Current conflicts are simplistic.

Future system should model:

- semantic contradiction
- protocol mismatch
- parser ambiguity
- entity-category disagreement
- low parse quality
- weak evidence overlap

---

# Future AI Layer

## IMPORTANT

AI is NOT the primary classifier.

AI is the validator.

---

# Planned AI Responsibilities

## AI SHOULD:

- validate deterministic output
- explain classifications
- resolve ambiguity
- identify semantic mismatches
- adjust confidence
- handle unseen patterns
- identify suspicious protocol anomalies

## AI SHOULD NOT:

- classify blindly from raw narration
- replace deterministic parsing
- replace semantic extraction
- replace protocol intelligence

---

# Planned AI Architecture

```text
Deterministic Output
        ↓
Confidence Filter
        ↓
Low Confidence Rows Only
        ↓
LLM Validation Prompt
        ↓
AI Validation Output
        ↓
Final Classification Merge
```

---

# Planned AI Prompt Structure

The AI should receive structured semantic context.

Example:

```json
{
  "narration": "UPI/12345/P2M/IRCTC@YBL",
  "mode": "UPI",
  "subtype": "P2M",
  "direction": "OUT",
  "entity": "IRCTC",
  "entity_type": "TRAVEL",
  "current_category": "PAYMENT GATEWAY",
  "confidence": 0.65,
  "conflicts": []
}
```

This dramatically improves AI reasoning quality.

---

# Critical Engineering Principles

## 1. Deterministic Before AI

Always attempt deterministic semantic extraction first.

---

## 2. Explainability Matters

Every classification should be explainable.

The engine should always expose:

- decision path
- confidence
- matched rules
- semantic evidence

---

## 3. Protocol Semantics > Keyword Matching

Structured protocol metadata is more reliable than narration keywords.

Prefer:

```python
subtype == "P2M"
```

over:

```python
"PAY" in narration
```

---

## 4. Semantic Precision > Rule Count

Adding more weak rules is dangerous.

Precision matters more than quantity.

---

## 5. Token-Safe Matching Mandatory

Never use naive substring matching.

Always use boundary-aware semantic matching.

---

## 6. Confidence Must Reflect Uncertainty

Weak semantic evidence should produce lower confidence.

The system must model ambiguity honestly.

---

# Common Failure Modes

## Dangerous Substring Matching

BAD:

```text
REV inside FOREVER
```

BAD:

```text
GAS inside RANGASAISRAVANTH
```

The engine must avoid semantic leakage.

---

# Current Weak Areas

## Merchant Coverage

Entity intelligence currently has low coverage.

---

## Bank-Specific Formats

Many banks use highly inconsistent narration structures.

Need more parser specialization.

---

## Transfer Semantics

Some transfers remain semantically ambiguous.

Need:

- richer subtype intelligence
- entity-aware transfer reasoning
- counterparty understanding

---

# Long-Term Vision

The long-term goal is to evolve this into:

# A Financial Semantic Intelligence Platform

Capabilities may eventually include:

- fraud signal detection
- transaction clustering
- behavioral analysis
- spend analytics
- semantic search
- anomaly detection
- account intelligence
- auto-generated financial summaries
- AI financial copilots

The current engine is intended to become the semantic foundation for these systems.

---

# Development Priorities (Recommended Order)

## Phase 1 — Deterministic Expansion

- parser coverage
- entity intelligence
- ontology expansion
- subtype semantics
- merchant normalization
- protocol specialization

## Phase 2 — AI Validation Layer

- low-confidence routing
- semantic validation
- confidence correction
- reasoning generation

## Phase 3 — Productionization

- caching
- observability
- metrics
- evaluation pipelines
- benchmark datasets
- semantic regression testing

## Phase 4 — Advanced Intelligence

- embeddings
- semantic memory
- clustering
- anomaly detection
- behavior modeling

---

# Final Philosophy

This project is NOT:

```text
"a regex categorizer"
```

It is:

# a structured semantic financial intelligence engine

The deterministic semantic layer is the foundation.

AI is an augmentation layer.

Explainability, semantic precision, protocol understanding, and confidence modeling are core architectural priorities.

