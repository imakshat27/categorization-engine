# Financial Transaction Intelligence Engine

Deterministic semantic intelligence for noisy, real-world banking transactions.

This project classifies bank statement narrations into a fixed financial taxonomy using protocol-aware parsing, semantic facts, entity intelligence, ranked evidence, conflict detection, and deterministic confidence modeling.

It is intentionally not an LLM-first categorizer.

AI is a validation and refinement layer. The deterministic engine owns classification.

---

## What This Is

Bank narrations are compact protocol messages, not ordinary prose. A single row can encode:

- payment rail
- protocol family
- reference number
- debit or credit direction
- counterparty
- bank hint
- UPI handle
- cheque lifecycle state
- bounce or reversal status
- merchant or lender identity
- bank-specific narration format

The engine turns those fragments into structured semantic facts, then classifies from evidence.

```text
Raw bank narration
    -> normalization
    -> protocol detection
    -> protocol-aware parsing
    -> semantic fact extraction
    -> entity intelligence
    -> evidence generation
    -> ranked hypotheses
    -> conflict detection
    -> deterministic confidence
    -> final category
    -> optional AI refinement
```

The guiding idea is simple:

```text
Parse first. Understand structure. Classify with evidence. Let AI advise, not decide blindly.
```

---

## Core Principles

### Deterministic First

The deterministic system performs the heavy lifting:

- text normalization
- protocol parsing
- entity recognition
- movement and intent extraction
- evidence scoring
- conflict modeling
- confidence calculation
- final taxonomy assignment

AI never replaces this layer. It validates, flags gaps, and suggests deterministic improvements.

### Protocol Semantics Beat Keywords

Prefer this:

```python
facts["protocol"]["rail"] == "UPI"
facts["protocol"]["subtype"] == "REV"
```

Avoid this:

```python
"UPI" in narration
"REV" in narration
```

### Token-Safe Matching Is Mandatory

Naive substring matching leaks semantics.

Bad:

```python
"REV" in "FOREVER STORE"
"GAS" in "RANGASAISRAVANTH"
```

Good:

```python
token_match("REV", narration)
token_match("GAS", narration)
```

Boundary-aware utilities live in `engine/matcher.py`.

### No First-Match Wins

The classifier does not stop at the first matching rule. It builds evidence for all plausible categories, ranks candidates, applies precedence and penalties, records conflicts, and exposes alternatives.

---

## Architecture

```text
app.py
  -> engine.loader.load_transactions
  -> engine.pipeline.process_transactions
      -> engine.normalizer.normalize_text
      -> engine.semantic.build_semantic_facts
          -> engine.parser.parse_transaction
          -> entity facts
          -> movement facts
          -> intent facts
          -> bank-family facts
      -> engine.classifier.classify_transaction
          -> engine.evidence_engine.classify_facts
              -> evidence items
              -> ranked candidates
              -> conflicts
              -> confidence
              -> review flags
  -> optional AI refinement
```

### Primary Output Columns

| Column | Meaning |
|---|---|
| `Category` | Final deterministic category |
| `Confidence` | Deterministic confidence score |
| `Decision Path` | Evidence reasons supporting the winner |
| `Conflicts` | Ambiguities or contradictions |
| `Ranked Candidates` | Candidate categories with scores |
| `Alternative Categories` | Strong non-winning candidates |
| `Review Required` | Manual review flag |
| `Review Reason` | Short conflict/review explanation |
| `Evidence Summary` | Detailed evidence provenance |

---

## Supported Taxonomy

The engine always classifies into one approved category from `engine/taxonomy.py`.

| Categories | Categories | Categories | Categories |
|---|---|---|---|
| ACH BOUNCED CHARGES | ATM DEPOSIT | ATM WITHDRAWAL | AUTO SWEEP |
| BANK CHARGES | CASH DEPOSIT | CASH WITHDRAWAL | CHEQUE BOUNCE - NON TECHNICAL |
| CHEQUE BOUNCE - TECHNICAL | CHEQUE CASH WITHDRAWAL | CHEQUE DEPOSIT | CHEQUE WITHDRAWAL |
| CREDIT CARD PAYMENT | DEBIT CARD TRANSFER IN | DEBIT CARD TRANSFER OUT | DEMAND DRAFT |
| E-COMMERCE | ECS BOUNCED CHARGES | ELECTRONIC FUND TRANSFER | FIXED DEPOSIT |
| FUEL | IMPS BOUNCE CHARGES | IMPS BOUNCE | INSURANCE |
| INTEREST | INVESTMENTS | LOAN | NEFT BOUNCE |
| PAYMENT GATEWAY | RECHARGE | REFUND OR REVERSAL | RTGS BOUNCE |
| SALARY PAID | SALARY RECEIVED | SALARY | TAX |
| TRANSFER IN | TRANSFER OUT | TRAVEL | UTILITY |

Taxonomy policy includes:

- approved category set
- category families
- category precedence
- fallback policy
- compatibility rules
- parser quality multipliers
- confidence penalties
- review threshold

---

## Current Capabilities

### Normalization

Normalizes raw narration text while preserving useful protocol structure.

```text
upi/12345/p2m/amazon@apl
```

becomes:

```text
UPI/12345/P2M/AMAZON@APL
```

### Protocol-Aware Parsing

The parser understands different narration families instead of treating every row as generic text.

Current rail and format coverage includes:

- UPI
- IMPS
- NEFT
- RTGS
- ACH and ACH debit
- ECS/NACH text formats
- ATM
- cheque/clearing patterns
- direct debit text
- payout/internal transfer families
- sweep/fixed deposit families

Example:

```text
ACHDEBIT:PY3001UV0000485FEB24,TVS CREDIT SERVICES
```

Parsed as:

| Field | Value |
|---|---|
| Rail | ACH |
| Family | ACH_DEBIT |
| Reference ID | PY3001UV0000485FEB24 |
| Counterparty | TVS CREDIT SERVICES |

With entity intelligence, this can classify as `LOAN` instead of falling back to generic `TRANSFER OUT`.

### Semantic Facts

`engine/semantic.py` builds one structured facts object per row:

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

These facts separate what happened from how the final category is chosen.

### Entity Intelligence

`engine/entity_registry.py` maps known counterparties to semantic categories.

Examples:

| Entity | Category | Role |
|---|---|---|
| IRCTC | TRAVEL | merchant |
| LIC | INSURANCE | insurer |
| AMAZON | E-COMMERCE | merchant |
| AIRTEL | RECHARGE | telecom |
| TVS CREDIT SERVICES | LOAN | lender |
| BAJAJ FINANCE | LOAN | lender |

Strong entity evidence can override generic rail evidence, while ambiguous payment-channel evidence is intentionally weaker.

### Evidence Engine

`engine/evidence_engine.py` converts semantic facts into category evidence.

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

The evidence engine:

- groups evidence by category
- ranks candidate hypotheses
- applies category precedence
- detects ambiguity
- computes deterministic confidence
- marks review-required rows

### Conflict Detection

Conflicts preserve ambiguity instead of hiding it.

Examples:

| Conflict | Meaning |
|---|---|
| `parser_low_quality` | Winning evidence depends on weak parsing |
| `weak_fallback` | Category came from fallback evidence |
| `competing_hypotheses` | Candidate scores are close |
| `rail_entity_ambiguity` | Rail and entity point to different category families |
| `processor_entity_ambiguity` | Payment processor may be channel, not final intent |

### Confidence Modeling

Confidence is deterministic and explainable.

It is affected by:

- evidence strength
- source weights
- parser quality
- category precedence
- conflicts
- fallback usage
- entity confidence

AI confidence is advisory only and does not replace deterministic confidence.

---

## AI Refinement

AI refinement is optional, stateless, and advisory.

The Streamlit app exposes an `AI Refinement` button after deterministic classification. The deterministic table is not overwritten. AI results appear in a separate triage table.

### Routing Policies

| Policy | Behavior |
|---|---|
| `strict` | Minimal calls. Suppresses weak entity-gap rows unless there is stronger ambiguity. |
| `balanced` | Default. Routes meaningful entity/parser/evidence gaps and skips low-value generic rows. |
| `exploratory` | Routes more ambiguous rows for discovery and rule mining. |

Rows are routed when there is useful semantic context, such as:

- entity rule gaps
- parser gaps
- substantive category ambiguity
- weak deterministic evidence with context
- optional old-vs-new category disagreement

Rows are skipped when AI is unlikely to help, such as:

- generic transfer rows with no actionable semantic context
- known merchant/entity rows where the only conflict is background rail ambiguity
- payment-channel-only rows in balanced mode

### AI Decisions

The model must return one structured JSON object.

Supported AI decisions:

| Decision | Meaning |
|---|---|
| `NO_CHANGE` | Deterministic category appears correct |
| `SUGGEST_CHANGE` | Payload supports a safe category change candidate |
| `NEEDS_DETERMINISTIC_FIX` | The useful result is a parser/entity/evidence improvement, not a category override |
| `INSUFFICIENT_EVIDENCE` | Payload does not support a safe change or fix |

### UI Outcomes

The app shows user-facing outcomes instead of raw validator noise:

| Outcome | Meaning |
|---|---|
| `CATEGORY_CONFIRMED` | AI agrees with deterministic category |
| `CATEGORY_CHANGE_SUGGESTED` | AI suggests a safe alternative category |
| `ENGINE_FIX_NEEDED` | AI found a deterministic parser/entity/evidence gap |
| `INSUFFICIENT_EVIDENCE` | AI cannot safely advise |
| `INVALID_RESPONSE` | Malformed or unusable model output |

Rejected model output is hidden under a diagnostic expander instead of dominating the main table.

### Performance Defaults

The refinement layer is tuned for lower latency:

- category definitions are scoped per row through `allowed_categories`
- prompts are compact JSON
- Ollama output is capped with `num_predict`
- skipped rows are logged as one aggregate summary
- full prompt and payload logging is disabled by default
- full audit logs are available through the app checkbox

This keeps the normal path lean while preserving replay/debug capability when needed.

---

## Project Map

| Path | Purpose |
|---|---|
| `app.py` | Streamlit UI for upload, classification, and AI refinement |
| `engine/loader.py` | Excel loading helper |
| `engine/normalizer.py` | Narration normalization |
| `engine/matcher.py` | Token-safe matching utilities |
| `engine/parser.py` | Protocol-aware parser |
| `engine/semantic.py` | Semantic fact extraction |
| `engine/entity_registry.py` | Canonical entity and alias registry |
| `engine/evidence_engine.py` | Evidence generation, ranking, confidence, conflicts |
| `engine/classifier.py` | Classification facade |
| `engine/taxonomy.py` | Approved categories and policy constants |
| `engine/ai_refinement.py` | Local AI advisory refinement |
| `engine/huggingface_refinement.py` | Hosted-model refinement wrapper |
| `tests/` | Regression tests |

---

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. Run the App

```bash
venv/bin/streamlit run app.py
```

In the app:

1. Upload an Excel workbook.
2. Enter the sheet name.
3. Review parser output.
4. Review deterministic classification output.
5. Optionally run AI refinement.

Common local sample:

```text
data/375-EDIT.xlsx
```

Common sheet name:

```text
Xns Transactions
```

### 3. Run Tests

```bash
venv/bin/python -m unittest discover -s tests
```

### 4. Compile Check

```bash
venv/bin/python -m py_compile app.py engine/ai_refinement.py engine/parser.py engine/semantic.py
```

---

## Programmatic Usage

```python
import pandas as pd

from engine.pipeline import process_transactions

df = pd.read_excel("data/375-EDIT.xlsx", sheet_name="Xns Transactions")
processed = process_transactions(df)

print(
    processed[
        [
            "Narration",
            "Mode",
            "Protocol Family",
            "Entity Name",
            "Merchant",
            "Category",
            "Confidence",
            "Conflicts",
            "Ranked Candidates",
            "Review Required",
        ]
    ]
)
```

Run AI refinement programmatically:

```python
from engine.ai_refinement import refine_transactions

results = refine_transactions(
    processed,
    routing_policy="balanced",
    max_rows=25,
    log_detail="summary",
    log_skipped="summary",
)
```

---

## How To Improve Classification

Prefer this order when a row is wrong:

1. Improve parser coverage in `engine/parser.py`.
2. Add entity aliases in `engine/entity_registry.py`.
3. Add reusable semantic tags in `engine/semantic.py`.
4. Add evidence mapping in `engine/evidence_engine.py`.
5. Tune taxonomy policy in `engine/taxonomy.py`.
6. Add regression tests in `tests/`.

Avoid:

- direct category decisions from raw narration
- unsafe substring matching
- broad keyword expansion
- first-match logic
- silent confidence inflation
- AI-only category overrides

---

## Troubleshooting

### A Row Has The Wrong Category

Check these columns first:

1. `Parse Quality`
2. `Protocol Family`
3. `Parser Rule`
4. `Entity Name`
5. `Merchant`
6. `Entity Type`
7. `Entity Role`
8. `Intent Tags`
9. `Movement Tags`
10. `Bank Family`
11. `Ranked Candidates`
12. `Conflicts`
13. `Evidence Summary`

### A Merchant Is Not Recognized

Add it to `engine/entity_registry.py`:

```python
{
    "canonical": "MERCHANT NAME",
    "aliases": ["MERCHANT NAME", "MERCHANT ALIAS"],
    "category": "E-COMMERCE",
    "role": "merchant",
    "confidence": 0.88,
    "ambiguity": "LOW",
}
```

Then add a test.

### A Protocol Format Parses Poorly

Update `engine/parser.py`, assign:

- `rail`
- `family`
- `parser_rule`
- `parse_quality`
- `parser_confidence`
- extracted fields such as `reference_id` and `counterparty`

Then add a parser test.

### AI Refinement Is Slow

Check:

- routing policy: use `strict` to minimize calls
- `max_rows`: lower it for interactive work
- audit logging: keep `Full audit logging` off unless debugging
- prompt scope: verify `category_definition_count` in logs
- local model performance: Ollama model latency still matters

### AI Says `ENGINE_FIX_NEEDED`

That is not a failure. It means the model found useful evidence, but the deterministic layer needs better parser/entity/evidence support before any category change should be trusted.

---

## Development Principles

### Keep Layers Separate

Do not collapse protocol, entity, movement, intent, and bank-family facts into a category too early.

Only the evidence engine should combine facts into final ranked hypotheses.

### Make Every Decision Explainable

Every meaningful signal should expose:

- source layer
- rule name
- matched value
- semantic reason
- confidence or strength

### Model Uncertainty Honestly

Weak parser quality, fallback evidence, close candidate scores, entity/rail disagreement, and payment-channel ambiguity should lower confidence or trigger review.

### Let AI Teach The Deterministic Engine

AI should help identify missing parser families, entity aliases, semantic tags, or evidence weights. Those discoveries should become deterministic code and tests.

---

## Current Priorities

1. Expand parser coverage for bank-specific narration families.
2. Grow the entity registry with aliases and roles.
3. Strengthen ACH/ECS/NACH and direct debit semantics.
4. Improve transfer counterparties and business-entity recognition.
5. Add more regression fixtures from real exports.
6. Keep AI refinement lean, advisory, and actionable.

---

## Verification Snapshot

Current verification commands:

```bash
venv/bin/python -m unittest discover -s tests
venv/bin/python -m py_compile app.py engine/ai_refinement.py engine/refinement_validator.py engine/parser.py engine/semantic.py
```

Recent coverage includes:

- token-safe matching
- protocol parser families
- ACH debit lender classification
- generic rail fallback
- entity-over-rail behavior
- payment-channel ambiguity
- old category labels as weak supervision only
- AI routing policies
- AI advisory outcomes
- compact AI payloads
- summary versus audit logging

---

## Philosophy

This is not a regex categorizer.

It is a semantic financial intelligence engine.

The deterministic layer should become increasingly rich, precise, and explainable. AI should make that deterministic layer better, not replace it.
