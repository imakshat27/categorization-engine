import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import pandas as pd

from engine.taxonomy import (
    APPROVED_CATEGORIES,
    APPROVED_CATEGORY_SET,
    REVIEW_CONFIDENCE_THRESHOLD,
)


DEFAULT_TRAINING_DATASET_PATH = "data/training_reviews.jsonl"

GENERIC_HIGH_VOLUME_CATEGORIES = {
    "ELECTRONIC FUND TRANSFER",
}

def _is_missing(value):
    if value is None:
        return True

    if isinstance(value, (dict, list, tuple, set)):
        return False

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _json_safe(value):
    if _is_missing(value):
        return None

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            _json_safe(item)
            for item in value
        ]

    if hasattr(value, "isoformat"):
        return value.isoformat()

    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def _row_value(row, key, default=""):
    if hasattr(row, "get"):
        value = row.get(key, default)
    else:
        value = default

    if _is_missing(value):
        return default

    return value


def _string_value(row, key, default=""):
    value = _row_value(row, key, default)

    if _is_missing(value):
        return default

    return str(value).strip()


def _bank_value(row):
    return (
        _string_value(row, "Bank")
        or _string_value(row, "Bank Name")
        or _string_value(row, "bank")
    )


def _narration_value(row):
    return _string_value(row, "Narration") or _string_value(row, "narration")


def _bool_value(value):
    if _is_missing(value):
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}

    return bool(value)


def _confidence_value(row):
    try:
        return float(_row_value(row, "Confidence", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _training_confidence_value(row):
    value = _row_value(
        row,
        "Confidence",
        _row_value(
            row,
            "confidence",
            _row_value(row, "deterministic_confidence", 0.0),
        ),
    )

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _training_direction(row):
    direction = (
        _string_value(row, "Direction")
        or _string_value(row, "direction")
    ).upper()

    direction_map = {
        "OUT": "DEBIT",
        "DR": "DEBIT",
        "DEBIT": "DEBIT",
        "IN": "CREDIT",
        "CR": "CREDIT",
        "CREDIT": "CREDIT",
    }

    return direction_map.get(direction, direction or "UNKNOWN")


def _pipe_values(value):
    if _is_missing(value) or value == "":
        return []

    if isinstance(value, str):
        return [
            item.strip()
            for item in value.split("|")
            if item.strip()
        ]

    if isinstance(value, (list, tuple, set)):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    return [
        str(value).strip()
    ]


def parse_ranked_candidates(value, limit=None):
    candidates = []

    if _is_missing(value) or value == "":
        return candidates

    if isinstance(value, (list, tuple)):
        raw_items = value
    else:
        raw_items = _pipe_values(value)

    for item in raw_items:
        if isinstance(item, dict):
            category = str(item.get("category", "")).strip()
            score = item.get("score")
        else:
            text = str(item).strip()

            if ":" in text:
                category, score = text.rsplit(":", 1)
            else:
                category, score = text, None

            category = category.strip()

        if not category:
            continue

        try:
            score = float(score)
        except (TypeError, ValueError):
            score = None

        candidates.append(
            {
                "category": category,
                "score": score,
            }
        )

        if limit and len(candidates) >= limit:
            break

    return candidates


def build_transaction_id(row):
    identity = {
        "bank": _bank_value(row),
        "narration": _narration_value(row),
    }

    serialized = json.dumps(
        identity,
        ensure_ascii=True,
        sort_keys=True,
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    return f"txn_{digest[:24]}"


def _has_conflicts(row):
    return bool(_pipe_values(_row_value(row, "Conflicts", "")))


def _old_category_disagreement(row):
    old_category = _string_value(row, "Old Category")
    category = _string_value(row, "Category")

    return bool(old_category and category and old_category != category)


def _candidate_margin_is_close(row):
    candidates = parse_ranked_candidates(
        _row_value(row, "Ranked Candidates", ""),
        limit=2,
    )

    if len(candidates) < 2:
        return False

    top_score = candidates[0].get("score")
    next_score = candidates[1].get("score")

    if top_score is None or next_score is None:
        return False

    return abs(top_score - next_score) < 0.08


def _category_counts(category_counts):
    if category_counts is None:
        return {}

    if isinstance(category_counts, Counter):
        return dict(category_counts)

    if isinstance(category_counts, dict):
        return category_counts

    return {}


def _is_rare_category(row, category_counts=None):
    counts = _category_counts(category_counts)
    category = _string_value(row, "Category")

    if not counts or not category:
        return False

    total = sum(counts.values())
    count = counts.get(category, 0)

    return count <= 2 or (total >= 100 and count / total <= 0.03)


def is_generic_high_confidence_transfer(row):
    category = _string_value(row, "Category")

    return (
        category in GENERIC_HIGH_VOLUME_CATEGORIES
        and _confidence_value(row) >= 0.85
        and not _has_conflicts(row)
        and not _bool_value(_row_value(row, "Review Required", False))
    )


def informative_flags_for_row(row, category_counts=None, final_category=None):
    flags = []
    category = _string_value(row, "Category")
    confidence = _confidence_value(row)
    entity_type = _string_value(row, "Entity Type", "UNKNOWN")

    if confidence < REVIEW_CONFIDENCE_THRESHOLD:
        flags.append("low_confidence")

    if _bool_value(_row_value(row, "Review Required", False)):
        flags.append("review_required")

    if _has_conflicts(row):
        flags.append("conflicted")

    if _candidate_margin_is_close(row):
        flags.append("close_candidates")

    if _old_category_disagreement(row):
        flags.append("old_category_disagreement")

    if _is_rare_category(row, category_counts=category_counts):
        flags.append("rare_category")

    if (
        category in GENERIC_HIGH_VOLUME_CATEGORIES
        and entity_type not in {"", "UNKNOWN"}
    ):
        flags.append("generic_category_with_entity_signal")

    if is_generic_high_confidence_transfer(row):
        flags.append("generic_high_confidence_transfer")

    if final_category and final_category != category:
        flags.append("corrected")

    return flags


def review_priority_score(row, category_counts=None, final_category=None):
    score = 0.0
    confidence = _confidence_value(row)

    if confidence < REVIEW_CONFIDENCE_THRESHOLD:
        score += 30.0
        score += (REVIEW_CONFIDENCE_THRESHOLD - confidence) * 80.0
    elif confidence < 0.8:
        score += 10.0

    if _bool_value(_row_value(row, "Review Required", False)):
        score += 25.0

    conflicts = _pipe_values(_row_value(row, "Conflicts", ""))
    if conflicts:
        score += 22.0 + min(len(conflicts), 4) * 4.0

    if _candidate_margin_is_close(row):
        score += 12.0

    if _old_category_disagreement(row):
        score += 18.0

    if _is_rare_category(row, category_counts=category_counts):
        score += 8.0

    if "generic_category_with_entity_signal" in informative_flags_for_row(
        row,
        category_counts=category_counts,
        final_category=final_category,
    ):
        score += 10.0

    if final_category and final_category != _string_value(row, "Category"):
        score += 35.0

    if is_generic_high_confidence_transfer(row):
        score -= 35.0

    return round(max(score, 0.0), 2)


def select_review_candidates(
    df,
    review_index=None,
    include_reviewed=False,
    hide_generic_high_confidence=True,
    review_required_only=False,
    conflict_only=False,
    category_filter=None,
    max_confidence=None,
    min_priority=0.0,
    max_rows=100,
):
    if df is None or df.empty:
        return pd.DataFrame()

    review_index = review_index or {}
    category_filter = set(category_filter or [])
    working = df.copy()

    if "Category" in working.columns:
        category_counts = Counter(
            str(category)
            for category in working["Category"]
            if not _is_missing(category)
        )
    else:
        category_counts = Counter()

    working["Transaction ID"] = [
        build_transaction_id(row)
        for _, row in working.iterrows()
    ]
    working["Already Reviewed"] = working["Transaction ID"].isin(review_index)
    working["Review Priority"] = [
        review_priority_score(row, category_counts=category_counts)
        for _, row in working.iterrows()
    ]
    working["Priority Flags"] = [
        " | ".join(
            informative_flags_for_row(
                row,
                category_counts=category_counts,
            )
        )
        for _, row in working.iterrows()
    ]
    working["_Confidence Sort"] = [
        _confidence_value(row)
        for _, row in working.iterrows()
    ]

    mask = pd.Series(True, index=working.index)

    if not include_reviewed:
        mask &= ~working["Already Reviewed"]

    if hide_generic_high_confidence:
        generic_mask = pd.Series(
            [
                is_generic_high_confidence_transfer(row)
                for _, row in working.iterrows()
            ],
            index=working.index,
        )
        mask &= ~generic_mask

    if review_required_only:
        mask &= working.apply(
            lambda row: _bool_value(_row_value(row, "Review Required", False)),
            axis=1,
        )

    if conflict_only:
        mask &= working.apply(_has_conflicts, axis=1)

    if category_filter and "Category" in working.columns:
        mask &= working["Category"].isin(category_filter)

    if max_confidence is not None:
        mask &= working["_Confidence Sort"] <= float(max_confidence)

    if min_priority:
        mask &= working["Review Priority"] >= float(min_priority)

    selected = working[mask].copy()
    selected = selected.sort_values(
        by=["Review Priority", "_Confidence Sort"],
        ascending=[False, True],
    )

    if max_rows:
        selected = selected.head(int(max_rows))

    return selected.drop(columns=["_Confidence Sort"])


def available_review_categories(
    df,
    review_index=None,
    include_reviewed=False,
    hide_generic_high_confidence=True,
    review_required_only=False,
    conflict_only=False,
    max_confidence=None,
    min_priority=0.0,
):
    candidates = select_review_candidates(
        df,
        review_index=review_index,
        include_reviewed=include_reviewed,
        hide_generic_high_confidence=hide_generic_high_confidence,
        review_required_only=review_required_only,
        conflict_only=conflict_only,
        category_filter=None,
        max_confidence=max_confidence,
        min_priority=min_priority,
        max_rows=None,
    )

    if candidates.empty or "Category" not in candidates.columns:
        return []

    available = {
        str(category).strip()
        for category in candidates["Category"]
        if not _is_missing(category) and str(category).strip()
    }

    return [
        category
        for category in APPROVED_CATEGORIES
        if category in available
    ]


def _ai_suggestion_from_row(row):
    fields = (
        "AI Decision",
        "AI Suggested Category",
        "Refinement Type",
        "AI Semantic Reason",
        "AI Rule Suggestion",
        "AI Missing Signal",
        "AI Confidence Advisory",
        "Validation Status",
    )
    suggestion = {}

    for field in fields:
        value = _row_value(row, field, "")

        if not _is_missing(value) and value != "":
            suggestion[field] = _json_safe(value)

    return suggestion


def build_training_record(
    row,
    final_category,
    feedback_source="streamlit_training_review",
    reviewer="",
    feedback_note="",
    row_index=None,
    reviewed_at=None,
    category_counts=None,
):
    final_category = str(final_category).strip()

    if final_category not in APPROVED_CATEGORY_SET:
        raise ValueError(f"Unapproved category: {final_category}")

    return {
        "bank": _bank_value(row),
        "narration": _narration_value(row),
        "direction": _training_direction(row),
        "predicted_category": _string_value(row, "Category", "UNKNOWN"),
        "confidence": _training_confidence_value(row),
        "correct_category": final_category,
    }


def normalize_review_record(record):
    if not isinstance(record, dict):
        return record

    return {
        "bank": _bank_value(record),
        "narration": _narration_value(record),
        "direction": _training_direction(record),
        "predicted_category": _string_value(
            record,
            "predicted_category",
            _string_value(record, "deterministic_category", "UNKNOWN"),
        ),
        "confidence": _training_confidence_value(record),
        "correct_category": _string_value(
            record,
            "correct_category",
            _string_value(
                record,
                "verified_category",
                _string_value(record, "final_verified_category", ""),
            ),
        ),
    }


def load_review_records(path=DEFAULT_TRAINING_DATASET_PATH):
    path = Path(path)

    if not path.exists():
        return []

    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if isinstance(payload, dict):
            return [
                normalize_review_record(record)
                for record in payload.get("records", [])
            ]

        if isinstance(payload, list):
            return [
                normalize_review_record(record)
                for record in payload
            ]

        raise ValueError(f"Unsupported JSON corpus shape: {path}")

    records = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                records.append(normalize_review_record(json.loads(line)))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL record at {path}:{line_number}"
                ) from exc

    return records


def load_review_index(path=DEFAULT_TRAINING_DATASET_PATH):
    index = {}

    for record in load_review_records(path):
        transaction_id = record.get("transaction_id") or build_transaction_id(record)

        if transaction_id:
            index[transaction_id] = record

    return index


def write_review_records(records, path=DEFAULT_TRAINING_DATASET_PATH):
    path = Path(path)
    records = [
        normalize_review_record(record)
        for record in records
    ]

    if path.parent:
        os.makedirs(path.parent, exist_ok=True)

    temp_path = path.with_suffix(f"{path.suffix}.tmp")

    if path.suffix.lower() == ".json":
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(
                records,
                file,
                indent=2,
                sort_keys=True,
            )
            file.write("\n")
    else:
        with temp_path.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(
                    json.dumps(
                        record,
                        ensure_ascii=True,
                        sort_keys=True,
                    )
                )
                file.write("\n")

    os.replace(temp_path, path)


def upsert_review_records(
    new_records,
    path=DEFAULT_TRAINING_DATASET_PATH,
    allow_updates=False,
):
    existing_records = load_review_records(path)
    order = []
    index = {}

    for record in existing_records:
        transaction_id = record.get("transaction_id") or build_transaction_id(record)

        if not transaction_id:
            continue

        if transaction_id not in index:
            order.append(transaction_id)

        index[transaction_id] = record

    stats = {
        "inserted": 0,
        "updated": 0,
        "skipped_duplicates": 0,
    }

    for record in new_records:
        transaction_id = record.get("transaction_id") or build_transaction_id(record)

        if not transaction_id:
            continue

        if transaction_id in index and not allow_updates:
            stats["skipped_duplicates"] += 1
            continue

        if transaction_id in index:
            index[transaction_id] = record
            stats["updated"] += 1
        else:
            order.append(transaction_id)
            index[transaction_id] = record
            stats["inserted"] += 1

    write_review_records(
        [
            index[transaction_id]
            for transaction_id in order
            if transaction_id in index
        ],
        path=path,
    )

    return stats


def training_corpus_stats(records):
    categories = Counter(
        record.get("correct_category", "UNKNOWN")
        for record in records
    )
    corrections = sum(
        1
        for record in records
        if record.get("correct_category") != record.get("predicted_category")
    )

    return {
        "total": len(records),
        "corrections": corrections,
        "accepted_deterministic": len(records) - corrections,
        "category_counts": dict(categories),
    }


def records_to_jsonl(records):
    return "\n".join(
        json.dumps(
            record,
            ensure_ascii=True,
            sort_keys=True,
        )
        for record in records
    )
