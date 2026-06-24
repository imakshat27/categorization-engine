# Financial Transaction Intelligence Engine

Deterministic semantic classification for real-world banking transactions.

This project is a financial transaction intelligence engine for BFSI workflows. It classifies noisy bank statement narrations into a fixed taxonomy of transaction categories using protocol-aware parsing, entity intelligence, semantic evidence, ranked hypotheses, deterministic confidence modeling, and explainable provenance.

The system is intentionally not an LLM-first classifier. AI refinement is advisory and runs only after deterministic semantic classification.

---

## Purpose

Bank statement narrations are not ordinary text. They often encode payment rails, references, handles, bank hints, counterparty names, lifecycle events, reversal states, cheque statuses, debit/credit direction, and bank-specific formats.

The goal of this project is to classify transactions accurately and explainably by understanding those structures.

This project is not:

```text
a keyword categorizer
```

It is:

```text
a structured semantic financial intelligence engine
```

The engine should:

- normalize raw transaction narrations
- parse protocol-specific narration formats
- extract semantic facts once
- keep protocol, entity, movement, and intent semantics separate
- build category evidence from structured facts
- rank candidate category hypotheses
- model confidence and conflicts deterministically
- expose explainable decision paths
- always classify into the approved taxonomy

---

## Core Philosophy

### Deterministic First

The deterministic engine is the foundation. It performs the heavy lifting:

- normalization
- protocol detection
- protocol-aware parsing
- entity recognition
- movement semantics
- intent semantics
- evidence generation
- hypothesis scoring
- confidence modeling

AI should not be the primary classifier. The AI refinement layer should only validate low-confidence, conflicted, or ambiguous deterministic outputs.

### Structured Facts Before Classification

Raw narration text should be interpreted as early as possible.

The downstream classifier should consume structured semantic metadata instead of repeatedly reparsing narration strings.

The intended flow is:

```text
Raw Narration
    ↓
Normalized Narration
    ↓
Protocol-Aware Parser
    ↓
Semantic Facts
    ↓
Evidence Items
    ↓
Ranked Candidate Hypotheses
    ↓
Final Classification
```

### No First-Match Wins

The classifier does not return the first matching rule.

Instead, it builds evidence for all plausible categories, ranks candidate hypotheses, applies confidence adjustments, records conflicts, and exposes alternatives.

### Token-Safe Matching

All semantic matching must be boundary-aware.

Bad:

```python
"REV" in narration
```

This incorrectly matches:

```text
FOREVER
```

Good:

```python
token_match("REV", narration)
```

Matching utilities live in `engine/matcher.py`.

---

## Approved Categories

The engine must classify into one of these categories:

```text
ACH BOUNCED CHARGES
ATM DEPOSIT
ATM WITHDRAWAL
AUTO SWEEP
BANK CHARGES
CASH DEPOSIT
CASH WITHDRAWAL
CHEQUE BOUNCE - NON TECHNICAL
CHEQUE BOUNCE - TECHNICAL
CHEQUE CASH WITHDRAWAL
CHEQUE DEPOSIT
CHEQUE WITHDRAWAL
CREDIT CARD PAYMENT
DEBIT CARD TRANSFER IN
DEBIT CARD TRANSFER OUT
DEMAND DRAFT
E-COMMERCE
ECS BOUNCED CHARGES
ELECTRONIC FUND TRANSFER
FIXED DEPOSIT
FUEL
IMPS BOUNCE CHARGES
IMPS BOUNCE
INSURANCE
INTEREST
INVESTMENTS
LOAN
NEFT BOUNCE
PAYMENT GATEWAY
RECHARGE
REFUND OR REVERSAL
RTGS BOUNCE
SALARY PAID
SALARY RECEIVED
SALARY
TAX
TRANSFER IN
TRANSFER OUT
TRAVEL
UTILITY
```

The canonical list, category families, precedence, fallback policy, confidence penalties, and review threshold are defined in `engine/taxonomy.py`.

---

## Documentation

For deep-dives into the pipeline's operational logic and training paradigms, refer to our expanded documentation inside the `docs/` folder:

- **[docs/system_flow.md](docs/system_flow.md):** A deeply detailed step-by-step pipeline reference mapping the ingestion, deterministic steps, logic application, evidence engine, and the AI validation layer to their exact scripts. Includes architecture flowcharts.
- **[docs/training_guidelines.md](docs/training_guidelines.md):** Exact methodology for data preparation (`finetuning/prepare_dataset.py`), the review routing logic, and the 11 core training guidelines to prevent LLM overfitting or script-induced bias. Includes fine-tuning pipeline flowcharts.
- **[docs/setup_and_run.md](docs/setup_and_run.md):** Simple Windows-focused quickstart instructions.

---

## High-Level Architecture

```text
app.py / uploaded file
    ↓
engine.loader.load_transactions
    ↓
engine.pipeline.process_transactions
    ↓
engine.normalizer.normalize_text
    ↓
engine.semantic.build_semantic_facts
        ├── engine.parser.parse_transaction
        ├── protocol facts
        ├── entity facts
        ├── movement facts
        ├── intent facts
        └── bank-family facts
    ↓
engine.classifier.classify_transaction
    ↓
engine.evidence_engine.classify_facts
        ├── build evidence items
        ├── rank category hypotheses
        ├── detect conflicts
        ├── compute confidence
        └── mark review-required rows
    ↓
processed dataframe with final Category and explanation fields
```

---

## Project Structure

```text
categorization-engine/
│
├── app.py
├── requirements.txt
├── README.md
├── AGENTS.md
│
├── docs/
│   ├── setup_and_run.md
│   ├── system_flow.md
│   └── training_guidelines.md
│
├── data/
│   └── 375-EDIT.xlsx
│
├── engine/
│   ├── classifier.py
│   ├── confidence.py
│   ├── entity_intelligence.py
│   ├── entity_registry.py
│   ├── evidence_engine.py
│   ├── loader.py
│   ├── matcher.py
│   ├── normalizer.py
│   ├── parser.py
│   ├── pipeline.py
│   ├── protocols.py
│   ├── rules.py
│   ├── semantic.py
│   ├── signals.py
│   └── taxonomy.py
│
├── rules/
│   ├── category_rules.json
│   ├── merchant_rules.json
│   └── mode_rules.json
│
└── tests/
    └── test_semantic_engine.py
```

---

## Module Guide

### `app.py`

Streamlit application entrypoint.

Responsibilities:

- configure the web page
- accept uploaded Excel files
- accept a sheet name
- load raw transaction rows
- run the processing pipeline
- display parsing output
- display classification output

Important output columns include:

- `Category`
- `Confidence`
- `Decision Path`
- `Conflicts`
- `Ranked Candidates`
- `Alternative Categories`
- `Review Required`
- `Review Reason`
- `Evidence Summary`

The final category shown to the user is the `Category` column.

---

### `engine/loader.py`

Excel loading helper.

Responsibilities:

- read an Excel sheet into a pandas dataframe
- strip whitespace from column names

Expected input columns include:

- `Narration`
- `Debits`
- `Credits`

Other useful columns include:

- `Bank`
- `Bank Code`
- `XN Date`
- `Cheque No`
- `Remarks`
- `Balance`

---

### `engine/normalizer.py`

Raw text normalization layer.

Responsibilities:

- handle empty/null narration values
- convert text to uppercase
- strip leading/trailing spaces
- collapse repeated whitespace
- standardize separators

Example:

```text
upi/12345/p2m/amazon@apl
```

becomes:

```text
UPI/12345/P2M/AMAZON@APL
```

Normalization is intentionally lightweight. It should improve parser consistency without destroying useful protocol structure.

---

### `engine/matcher.py`

Shared token-safe matching utilities.

Responsibilities:

- compile boundary-aware token patterns
- match single tokens
- match phrases across common separators
- run regex matches with provenance metadata
- clean extracted entity text
- avoid unsafe substring matching

Important functions:

- `token_pattern(term)`
- `token_match(term, text, ...)`
- `first_token_match(terms, text, ...)`
- `any_token_match(terms, text, ...)`
- `regex_match(pattern, text, ...)`
- `clean_entity_text(text)`

Rules should use this module instead of direct substring checks.

---

### `engine/taxonomy.py`

Canonical category and classification policy definitions.

Responsibilities:

- define the 40 approved categories
- define semantic category families
- define category precedence
- define generic rail fallback categories
- define fallback categories by money direction
- define parser-quality confidence multipliers
- define conflict penalties
- define the review confidence threshold

Important constants:

- `APPROVED_CATEGORIES`
- `APPROVED_CATEGORY_SET`
- `CATEGORY_FAMILIES`
- `CATEGORY_PRECEDENCE`
- `RAIL_CATEGORIES`
- `FALLBACK_CATEGORY_BY_DIRECTION`
- `PARSER_QUALITY_MULTIPLIER`
- `CONFLICT_PENALTIES`
- `REVIEW_CONFIDENCE_THRESHOLD`

This file is the best place to understand the final output taxonomy.

---

### `engine/parser.py`

Protocol-aware parser.

Responsibilities:

- parse normalized narration once
- identify rail/protocol family
- extract reference IDs
- extract counterparty/entity text
- extract bank hints
- extract UPI IDs and handles
- extract cheque/instrument numbers where possible
- assign parser rule, parser confidence, and parse quality
- preserve legacy output fields for the UI

Parser output contains both legacy and semantic fields:

```python
{
    "transaction_prefix": "...",
    "transaction_subtype": "...",
    "reference_id": "...",
    "entity_name": "...",
    "bank_name": "...",
    "upi_id": "...",
    "upi_handle": "...",
    "parse_quality": "...",
    "rail": "...",
    "family": "...",
    "subtype": "...",
    "counterparty": "...",
    "bank": "...",
    "instrument_no": "...",
    "handle": "...",
    "parser_rule": "...",
    "parser_confidence": ...
}
```

Supported parser families include:

- `UPI_RRN`
- `UPI_SLASH`
- `UPI_REVERSAL`
- `IMPS_RECEIVED`
- `IMPS_SENT`
- `IMPS_P2A`
- `IMPS_GENERIC`
- `NEFT`
- `RTGS`
- `ATM`
- `CHEQUE`
- `ACH`
- `ECS_NACH`
- `DIRECT_DEBIT`
- `PAYOUT`
- `SWEEP_FIXED_DEPOSIT`

Parser quality values:

- `HIGH`
- `MEDIUM`
- `LOW`

Parser quality directly affects final confidence when the winning hypothesis depends on parser-derived evidence.

---

### `engine/entity_registry.py`

Structured entity and merchant registry.

Responsibilities:

- define canonical entities
- define aliases
- map entities to semantic categories
- define entity role
- define entity confidence
- define ambiguity level

Entity fields:

```python
{
    "canonical": "AMAZON",
    "aliases": ["AMAZON", "AMAZON PAY"],
    "category": "E-COMMERCE",
    "role": "merchant",
    "confidence": 0.88,
    "ambiguity": "MEDIUM",
}
```

Entity roles include:

- `merchant`
- `payment_channel`
- `payment_processor`
- `wallet`
- `biller`
- `lender`
- `insurer`
- `telecom`
- `travel`
- `card_payment_app`

Important policy:

- strong merchant/biller/entity evidence can override generic rail evidence
- ambiguous payment-channel evidence is weaker
- payment apps should become `PAYMENT GATEWAY` only when they appear to be the processor/settlement entity

---

### `engine/entity_intelligence.py`

Compatibility wrapper around the structured entity registry.

Responsibilities:

- expose `detect_entity_type(entity_name)`
- return legacy-friendly fields used by existing UI/reporting code
- use token-safe matching through `engine.matcher`

Output fields:

- `entity_type`
- `entity_confidence`
- `matched_entity_rule`
- `entity_role`
- `entity_ambiguity`

New development should prefer semantic facts from `engine.semantic.build_semantic_facts`, but this module remains useful for compatibility.

---

### `engine/semantic.py`

Semantic fact builder.

This is the main extraction layer between normalized text and classification.

Responsibilities:

- call the protocol parser
- detect money direction from `Debits` and `Credits`
- detect rail terms
- detect movement tags
- detect intent tags
- detect bounce type
- detect entity semantics
- detect bank-specific narration families
- emit one structured semantic facts object per row

Semantic facts shape:

```python
{
    "protocol": {...},
    "entity": {...},
    "movement": {...},
    "intent": {...},
    "bank_family": {...},
    "matches": [...]
}
```

#### Protocol facts

Examples:

- `rail`
- `family`
- `subtype`
- `reference_id`
- `counterparty`
- `bank`
- `instrument_no`
- `handle`
- `parser_rule`
- `parse_quality`
- `parser_confidence`

#### Entity facts

Examples:

- `canonical`
- `category`
- `role`
- `confidence`
- `ambiguity`
- `matched_alias`

#### Movement facts

Examples:

- `direction`
- `direction_source`
- `tags`
- `instrument_type`

Movement tags include:

- `cash`
- `deposit`
- `withdrawal`
- `atm`
- `cheque`
- `manual_transfer`
- `debit_card`

#### Intent facts

Examples:

- `tags`
- `bounce_type`

Intent tags include:

- `reversal`
- `bounce`
- `charge`
- `salary`
- `tax`
- `interest`
- `investment`
- `insurance`
- `recharge`
- `travel`
- `utility`
- `loan`
- `fuel`
- `fixed_deposit`
- `auto_sweep`
- `credit_card_payment`
- `demand_draft`
- `direct_debit`

#### Bank-family facts

Examples:

- `KOTAK_PAYOUT`
- `SWEEP_FIXED_DEPOSIT`
- `CENTRAL_BANK_CASH_RECEIPT`
- `CHEQUE_CLEARING`
- `BANK_CHARGE`
- `DIRECT_DEBIT`
- `MANUAL_BENEFICIARY_TRANSFER`

This layer is where raw narration matching should mostly happen. Downstream classification should consume the semantic facts instead of re-reading narration text.

---

### `engine/evidence_engine.py`

Evidence generation, hypothesis ranking, conflict detection, and confidence scoring.

Responsibilities:

- convert semantic facts into evidence items
- group evidence by category
- rank candidate hypotheses
- detect ambiguity/conflicts
- compute confidence
- decide whether manual review is required
- return final classification output

#### Evidence item

Evidence item shape:

```python
{
    "category": "FUEL",
    "source": "entity",
    "strength": 0.93,
    "reason": "entity_merchant",
    "provenance": "entity.SUPER FILLINGS",
    "opposing": False,
}
```

Evidence sources:

- `intent`
- `entity`
- `protocol`
- `movement`
- `instrument`
- `bank_family`
- `fallback`

Source weights are defined in `SOURCE_WEIGHTS`.

#### Candidate hypothesis

Candidate hypotheses are ranked category options.

Each candidate contains:

- `category`
- `score`
- supporting evidence
- precedence

The highest-ranked candidate becomes the final `Category`.

#### Conflict detection

Conflicts lower confidence and improve explainability.

Current conflict examples:

- `deposit_withdrawal_conflict`
- `parser_low_quality`
- `weak_fallback`
- `competing_hypotheses`
- `rail_entity_ambiguity`
- `processor_entity_ambiguity`

#### Confidence

Confidence is derived from:

- winning candidate score
- source weights
- parser quality multiplier
- conflict penalties
- evidence strength

Confidence is not AI-generated.

#### Review required

`Review Required` becomes true when:

- confidence is below `REVIEW_CONFIDENCE_THRESHOLD`
- weak fallback was used
- top candidate scores are too close
- severe conflicts are present

---

### `engine/classifier.py`

Classification facade.

Responsibilities:

- expose compatibility functions:
  - `detect_mode`
  - `detect_merchant`
  - `detect_direction`
  - `resolve_category`
  - `classify_transaction`
- route final classification through semantic facts and the evidence engine

Important behavior:

- `classify_transaction(row)` expects `Semantic Facts` when available
- if facts are absent, it builds them from the row
- final classification is delegated to `engine.evidence_engine.classify_facts`

This keeps older call sites working while moving the real classification logic into the semantic evidence engine.

---

### `engine/pipeline.py`

Main dataframe processing pipeline.

Responsibilities:

- normalize narrations
- detect transaction direction
- build semantic facts once
- expose protocol/entity/movement/intent facts as dataframe columns
- run classification
- append final explanation fields

Important final output fields:

- `Category`
- `Confidence`
- `Matched Rule`
- `Decision Path`
- `Conflicts`
- `Ranked Candidates`
- `Alternative Categories`
- `Review Required`
- `Review Reason`
- `Evidence Summary`

The final category is assigned here:

```python
df["Category"] = classification_results.apply(lambda result: result["category"])
```

---

### `engine/signals.py`

Compatibility semantic signal helpers.

Responsibilities:

- expose boolean signal functions such as:
  - `detect_bounce`
  - `detect_charge`
  - `detect_reversal`
  - `detect_salary`
  - `detect_tax`
  - `detect_cash`
  - `detect_atm`
  - `detect_cheque`
  - `detect_investment`
  - `detect_insurance`
  - `detect_recharge`
  - `detect_travel`
  - `detect_utility`
  - `detect_loan`
- use token-safe matching
- preserve compatibility with older pipeline/reporting expectations

New classification logic should prefer semantic facts from `engine.semantic`.

---

### `engine/rules.py`

JSON rule loader.

Responsibilities:

- load `rules/category_rules.json`
- load `rules/mode_rules.json`
- load `rules/merchant_rules.json`

These JSON rule files remain available, but the newer semantic engine increasingly relies on structured facts, taxonomy, entity registry, and evidence scoring.

---

### `engine/protocols.py`

Protocol subtype constants.

Current subtype mapping includes:

- `P2M`
- `P2V`
- `REV`

This module is small today and can evolve into a richer protocol ontology.

---

### `engine/confidence.py`

Legacy confidence helper.

Responsibilities:

- build old-style classification dictionaries
- apply simple conflict penalties
- clamp confidence between `0.0` and `1.0`

The newer semantic engine uses `engine.evidence_engine` for candidate scoring and confidence. This module remains for compatibility with older code paths.

---

### `tests/test_semantic_engine.py`

Regression and unit tests for the semantic engine.

Coverage includes:

- token-safe matching
- parser family extraction
- generic rail classification
- entity-over-rail behavior
- payment-channel behavior
- old category labels not being treated as truth
- approved-taxonomy fallback
- representative paths for all 40 approved categories

Run with:

```bash
venv/bin/python -m unittest discover -s tests
```

---

## Classification Policy

### Generic Rail Movement

Generic rail transactions classify as `ELECTRONIC FUND TRANSFER` when no stronger semantic intent is present.

Rail examples:

- UPI
- IMPS
- NEFT
- RTGS

Example:

```text
UPI/RRN 412288007493/UPI
```

Typical category:

```text
ELECTRONIC FUND TRANSFER
```

### Strong Entity or Intent Override

Strong semantic evidence can override generic rail evidence.

Example:

```text
UPI/SUPER FILLINGS/425547609685/NA
```

Evidence:

- protocol rail: UPI
- entity: SUPER FILLINGS
- entity category: FUEL

Typical category:

```text
FUEL
```

Conflict:

```text
rail_entity_ambiguity
```

This conflict lowers confidence and preserves `ELECTRONIC FUND TRANSFER` as an alternative candidate.

### Payment Apps and Aggregators

Payment apps are not automatically final categories.

Policy:

- if the app is just a payment channel, it should not override the underlying transaction intent
- if the app/aggregator is the processor or settlement entity, it may support `PAYMENT GATEWAY`
- ambiguous payment processor evidence should reduce confidence or produce alternatives

Examples:

- PhonePe as channel: often stays `ELECTRONIC FUND TRANSFER`
- Razorpay settlement: may become `PAYMENT GATEWAY`
- Amazon Pay with purchase context: may become `E-COMMERCE`

### Manual and Non-Rail Transfers

Manual/internal transfer patterns use money direction.

Examples:

- `KOTAKPAYOUT-*`
- `FRM TRF`
- `TO TRF`
- `FUND TRF`
- `FRIEND OR FAMILY`
- raw beneficiary-bank narration

Typical categories:

- `TRANSFER IN`
- `TRANSFER OUT`

### Fallback

The engine always stays inside the approved taxonomy.

Fallback rules:

- known incoming direction: `TRANSFER IN`
- known outgoing direction: `TRANSFER OUT`
- unknown direction: `ELECTRONIC FUND TRANSFER`

Fallback rows are low confidence and marked for review.

---

## Confidence Model

Confidence is deterministic.

It is affected by:

- evidence strength
- evidence source weight
- number of supporting evidence items
- category precedence
- parser quality
- entity confidence
- conflicts
- fallback usage

Parser quality matters because a low-quality parser result should not produce high-confidence protocol conclusions.

Conflict penalties are defined in `engine/taxonomy.py`.

---

## Explainability Fields

The processed dataframe includes explanation fields:

### `Decision Path`

Short list of evidence reasons supporting the winning category.

Example:

```text
entity:entity_merchant | protocol:generic_rail_transfer
```

### `Conflicts`

Detected ambiguity or contradiction.

Example:

```text
rail_entity_ambiguity
```

### `Ranked Candidates`

All candidate categories ranked by score.

Example:

```text
FUEL:0.959 | ELECTRONIC FUND TRANSFER:0.689
```

### `Alternative Categories`

Top non-winning categories.

### `Review Required`

Boolean flag for rows that should be manually inspected.

### `Review Reason`

Human-readable conflict summary.

### `Evidence Summary`

Detailed evidence list showing category, source, reason, and strength.

---

## Weak Supervision Policy

Historical export files may contain a `Category` column from older logic.

That column should not be treated as semantic truth.

It may be used only as weak supervision:

- discovering common narration families
- identifying candidate rules
- comparing old and new outputs
- selecting rows for manual relabeling

It should not directly override the semantic engine.

The tests explicitly verify this behavior.

---

## Running the App

Install dependencies in the project virtual environment, then run:

```bash
venv/bin/streamlit run app.py
```

In the app:

1. Upload an Excel file.
2. Enter the sheet name.
3. Review parsing output.
4. Review final classification output.

Default sample workbook:

```text
data/375-EDIT.xlsx
```

Common sheet name:

```text
Xns Transactions
```

---

## Running Tests

Run the test suite:

```bash
venv/bin/python -m unittest discover -s tests
```

Compile-check engine and tests:

```bash
venv/bin/python -m compileall engine tests
```

---

## AI Refinement

AI refinement is optional, stateless, and advisory.

The Streamlit app exposes an `AI Refinement` button after deterministic classification. It routes only selected rows to the local model:

- low confidence
- review required
- conflicts
- optional old-vs-new category disagreement

The deterministic table is not overwritten. AI results appear in a separate refinement table.

Current local model target:

```text
Ollama qwen2.5:7b
```

The refinement layer uses:

- versioned compressed semantic payloads
- versioned taxonomy/category definitions
- versioned prompt templates
- strict AI output schema
- centralized deterministic validation
- replayable JSONL logs in `output/ai_refinement_logs.jsonl`

Invalid AI output is quarantined and excluded from accepted refinement results.

---

## Processing Data Programmatically

Example:

```python
import pandas as pd

from engine.pipeline import process_transactions

df = pd.read_excel("data/375-EDIT.xlsx", sheet_name="Xns Transactions")
processed = process_transactions(df)

print(processed[[
    "Narration",
    "Category",
    "Confidence",
    "Conflicts",
    "Ranked Candidates",
    "Review Required",
]])
```

---

## Adding a New Pattern

Prefer this order:

1. Add or improve parser support if the pattern represents a protocol structure.
2. Add an entity to `engine/entity_registry.py` if the pattern is a merchant, biller, lender, insurer, processor, or recognizable organization.
3. Add semantic intent or movement extraction in `engine/semantic.py` if the pattern represents a reusable semantic fact.
4. Add evidence mapping in `engine/evidence_engine.py` if a semantic fact should support a category.
5. Add or update tests in `tests/test_semantic_engine.py`.

Avoid:

- adding category decisions directly from raw narration in the classifier
- broad substring matching
- first-match logic
- uncontrolled keyword expansion
- rules without provenance

---

## Development Principles

### Keep Semantic Layers Separate

Do not collapse all evidence into a category too early.

Keep these layers independent:

- protocol semantics
- entity semantics
- movement semantics
- intent semantics
- bank-family semantics

Only the evidence engine should combine them into final ranked hypotheses.

### Prefer Semantic Facts

Once a fact has been extracted, downstream code should use the fact.

Good:

```python
facts["protocol"]["rail"] == "UPI"
```

Avoid:

```python
"UPI" in narration
```

### Make Rules Explainable

Every meaningful match should have provenance:

- source layer
- rule name
- matched value
- semantic reason
- confidence or strength

### Confidence Must Reflect Uncertainty

Ambiguity should not be hidden.

Examples that should lower confidence:

- low parser quality
- generic fallback
- close candidate scores
- rail/entity disagreement
- processor/channel ambiguity
- contradictory movement facts

### AI Refinement Layer

The advisory AI refinement layer receives compact semantic payloads like:

```json
{
  "semantic_payload_version": "2026-05-28.1",
  "narration": "UPI/SUPER FILLINGS/425547609685/NA",
  "semantic_summary": {
    "rail": "UPI",
    "protocol_family": "UPI_SLASH",
    "direction": "OUT",
    "entity_category": "FUEL",
    "intent_tags": ["fuel"]
  },
  "deterministic": {
    "category": "FUEL",
    "confidence": 0.88
  },
  "candidates": ["FUEL", "ELECTRONIC FUND TRANSFER"],
  "major_conflicts": ["rail_entity_ambiguity"]
}
```

AI should return structured advisory output such as `NO_CHANGE` or `SUGGEST_CHANGE`. It should not replace deterministic extraction or overwrite the deterministic `Category`.

The current local prototype target is Ollama with `qwen2.5:7b`.

---

## Current Limitations

The engine is now structured for semantic scaling, but coverage still depends on:

- parser family expansion
- entity registry growth
- more bank-specific narration families
- manually relabeled regression fixtures
- sharper payment-gateway versus merchant semantics
- richer cheque lifecycle modeling
- more examples for rare categories

The correct next step is not more if/else logic. The correct next step is improving structured facts, evidence weights, conflict modeling, and tests.

---

## Quick Troubleshooting

### A row has the wrong category

Check:

1. `Parse Quality`
2. `Protocol Family`
3. `Parser Rule`
4. `Entity Type`
5. `Entity Role`
6. `Intent Tags`
7. `Movement Tags`
8. `Bank Family`
9. `Ranked Candidates`
10. `Conflicts`
11. `Evidence Summary`

### A merchant is not recognized

Add it to `engine/entity_registry.py` with:

- canonical name
- aliases
- category
- role
- confidence
- ambiguity

Then add a test.

### A protocol format is parsed poorly

Update `engine/parser.py`.

Then add a parser test.

### A category appears as an alternative but does not win

Check:

- evidence strength
- source weights in `engine/evidence_engine.py`
- category precedence in `engine/taxonomy.py`
- conflicts and confidence penalties

---

## Verification Snapshot

The semantic refactor has been verified with:

```bash
venv/bin/python -m unittest discover -s tests
venv/bin/python -m compileall engine tests
```

The current tests cover representative paths for all 40 approved categories.
