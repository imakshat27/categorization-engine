import json
import os
import re
from datetime import datetime, timezone

import requests

from engine.refinement_contracts import (
    AI_OUTPUT_SCHEMA_VERSION,
    DETERMINISTIC_ENGINE_VERSION,
    DIAGNOSTIC_FLAGS,
    PROMPT_TEMPLATE_VERSION,
    REQUIRED_AI_FIELDS,
    SEMANTIC_PAYLOAD_VERSION,
)
from engine.refinement_validator import validate_ai_output
from engine.taxonomy import (
    CATEGORY_DEFINITION_VERSION,
    CATEGORY_DEFINITIONS,
    REVIEW_CONFIDENCE_THRESHOLD,
    TAXONOMY_VERSION,
)


DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_LOG_PATH = "output/ai_refinement_logs.jsonl"


def _pipe_values(value):
    if value in (None, ""):
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

    return [str(value).strip()]


def _confidence_band(confidence):
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return "UNKNOWN"

    if value >= 0.85:
        return "HIGH"

    if value >= REVIEW_CONFIDENCE_THRESHOLD:
        return "MEDIUM"

    return "LOW"


def _major_conflicts(row):
    return _pipe_values(row.get("Conflicts", ""))


def _top_candidates(row, limit=3):
    candidates = []

    for item in _pipe_values(row.get("Ranked Candidates", ""))[:limit]:
        if ":" not in item:
            candidates.append(
                {
                    "category": item,
                    "score": None,
                }
            )
            continue

        category, score = item.rsplit(":", 1)

        try:
            score = float(score)
        except ValueError:
            score = None

        candidates.append(
            {
                "category": category.strip(),
                "score": score,
            }
        )

    return candidates


def diagnostic_flags_for_row(row):
    flags = set()
    conflicts = set(_major_conflicts(row))
    confidence = row.get("Confidence", 0.0)
    parse_quality = row.get("Parse Quality", "LOW")
    entity_type = row.get("Entity Type", "UNKNOWN")
    review_required = bool(row.get("Review Required", False))

    if parse_quality == "LOW" or row.get("Parser Rule") == "NO_PARSER_MATCH":
        flags.add("SEMANTIC_EXTRACTION_FAILURE")

    if conflicts.intersection(
        {
            "rail_entity_ambiguity",
            "processor_entity_ambiguity",
            "competing_hypotheses",
            "entity_category_disagreement",
        }
    ):
        flags.add("ONTOLOGY_AMBIGUITY")

    if review_required or _confidence_band(confidence) == "LOW":
        flags.add("EVIDENCE_WEIGHT_WEAKNESS")

    if entity_type == "UNKNOWN" and _confidence_band(confidence) == "LOW":
        flags.add("SEMANTIC_EXTRACTION_FAILURE")

    return sorted(flags.intersection(DIAGNOSTIC_FLAGS))


def should_refine_row(row, threshold=REVIEW_CONFIDENCE_THRESHOLD, include_old_category_disagreement=True):
    try:
        confidence = float(row.get("Confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    if confidence < threshold:
        return True

    if bool(row.get("Review Required", False)):
        return True

    if _major_conflicts(row):
        return True

    if include_old_category_disagreement and "Old Category" in row:
        old_category = row.get("Old Category")
        category = row.get("Category")

        if old_category not in (None, "") and old_category != category:
            return True

    return False


def select_rows_for_refinement(df, threshold=REVIEW_CONFIDENCE_THRESHOLD, include_old_category_disagreement=True):
    mask = df.apply(
        lambda row: should_refine_row(
            row,
            threshold=threshold,
            include_old_category_disagreement=include_old_category_disagreement,
        ),
        axis=1,
    )

    return df[mask].copy()


def build_semantic_payload(row, row_index=None):
    payload = {
        "semantic_payload_version": SEMANTIC_PAYLOAD_VERSION,
        "payload_created_at": datetime.now(timezone.utc).isoformat(),
        "deterministic_engine_version": DETERMINISTIC_ENGINE_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "category_definition_version": CATEGORY_DEFINITION_VERSION,
        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
        "ai_output_schema_version": AI_OUTPUT_SCHEMA_VERSION,
        "row_index": row_index,
        "narration": row.get("Narration", ""),
        "normalized_narration": row.get("Normalized Narration", ""),
        "deterministic": {
            "category": row.get("Category", "UNKNOWN"),
            "confidence": row.get("Confidence", 0.0),
            "confidence_band": _confidence_band(row.get("Confidence", 0.0)),
            "review_required": bool(row.get("Review Required", False)),
        },
        "semantic_summary": {
            "rail": row.get("Mode", "UNKNOWN"),
            "protocol_family": row.get("Protocol Family", "UNKNOWN"),
            "direction": row.get("Direction", "UNKNOWN"),
            "counterparty": row.get("Entity Name", "UNKNOWN"),
            "entity_category": row.get("Entity Type", "UNKNOWN"),
            "entity_role": row.get("Entity Role", "UNKNOWN"),
            "entity_confidence": row.get("Entity Confidence", 0.0),
            "intent_tags": _pipe_values(row.get("Intent Tags", "")),
            "movement_tags": _pipe_values(row.get("Movement Tags", "")),
            "bank_family": row.get("Bank Family", "UNKNOWN"),
        },
        "candidates": _top_candidates(row),
        "major_conflicts": _major_conflicts(row),
        "diagnostic_flags": diagnostic_flags_for_row(row),
        "deterministic_evidence_summary": _pipe_values(row.get("Evidence Summary", "")),
        "category_definitions": CATEGORY_DEFINITIONS,
    }

    return payload


def build_refinement_prompt(payload):
    instruction = {
        "task": "Validate deterministic transaction categorization using only the compact semantic payload.",
        "rules": [
            "Return one JSON object only.",
            "All required fields must be top-level keys on the returned object.",
            "Do not wrap the response in instruction, output_schema, semantic_payload, response, result, or answer.",
            "Do not use markdown fences or add explanatory prose.",
            "Do not invent categories.",
            "Use NO_CHANGE when deterministic category is semantically correct.",
            "Keep semantic_reason short and ontology-aligned.",
            "Do not provide chain-of-thought or verbose reasoning.",
            "AI confidence is advisory only.",
        ],
        "required_top_level_fields": [
            "decision",
            "suggested_category",
            "refinement_type",
            "semantic_reason",
            "missing_or_misread_signal",
            "recommended_deterministic_improvement",
            "ai_confidence_advisory",
        ],
        "field_definitions": {
            "decision": "NO_CHANGE or SUGGEST_CHANGE",
            "suggested_category": "One approved category",
            "refinement_type": "ENTITY_OVERRIDE, AMBIGUITY_RESOLUTION, PARSER_GAP, WEAK_DETERMINISTIC_EVIDENCE, or NO_ISSUE_DETECTED",
            "semantic_reason": "Short ontology-aligned phrase",
            "missing_or_misread_signal": "Short phrase or empty string",
            "recommended_deterministic_improvement": "Short phrase or empty string",
            "ai_confidence_advisory": "LOW, MEDIUM, or HIGH",
        },
    }

    return json.dumps(
        {
            "instruction": instruction,
            "semantic_payload": payload,
        },
        indent=2,
        sort_keys=True,
    )


def _extract_json_object(text):
    if isinstance(text, dict):
        return text

    if not isinstance(text, str):
        raise ValueError("AI response is not text")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError("No JSON object found in AI response")

    return json.loads(match.group(0))


def _has_required_ai_fields(value):
    return isinstance(value, dict) and REQUIRED_AI_FIELDS.issubset(value)


def _value_at_path(value, path):
    current = value

    for key in path:
        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current


def _normalize_ai_output_shape(ai_output):
    if _has_required_ai_fields(ai_output):
        return ai_output

    wrapper_paths = [
        ("instruction", "output_schema"),
        ("output_schema",),
        ("response",),
        ("result",),
        ("answer",),
        ("refinement",),
    ]

    for path in wrapper_paths:
        candidate = _value_at_path(ai_output, path)

        if _has_required_ai_fields(candidate):
            return candidate

    if isinstance(ai_output, dict):
        for candidate in ai_output.values():
            if _has_required_ai_fields(candidate):
                return candidate

    return ai_output


def call_ollama(prompt, model=DEFAULT_OLLAMA_MODEL, base_url=DEFAULT_OLLAMA_URL, timeout=120):
    response = requests.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "top_p": 0.1,
            },
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def append_refinement_log(entry, log_path=DEFAULT_LOG_PATH):
    directory = os.path.dirname(log_path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry, sort_keys=True) + "\n")


def refine_row(
    row,
    row_index=None,
    model=DEFAULT_OLLAMA_MODEL,
    base_url=DEFAULT_OLLAMA_URL,
    generate_func=None,
    log_path=DEFAULT_LOG_PATH,
    provider="ollama",
):
    payload = build_semantic_payload(row, row_index=row_index)
    prompt = build_refinement_prompt(payload)
    generate = generate_func or (
        lambda prompt_text: call_ollama(
            prompt_text,
            model=model,
            base_url=base_url,
        )
    )

    raw_response = ""
    extracted_response = {}
    parsed_response = {}
    validation = {}

    try:
        raw_response = generate(prompt)
        extracted_response = _extract_json_object(raw_response)
        parsed_response = _normalize_ai_output_shape(extracted_response)
        validation = validate_ai_output(parsed_response, payload)
    except Exception as exc:
        validation = {
            "validation_status": "REJECTED",
            "validation_errors": [str(exc)],
            "validator_version": "UNAVAILABLE",
            "validated_output": {},
        }

    accepted = validation.get("validated_output", {})
    deterministic_category = payload["deterministic"]["category"]
    suggested_category = accepted.get("suggested_category", "")
    ai_decision = accepted.get("decision", "")
    diagnostic_flags = list(payload["diagnostic_flags"])

    if (
        validation.get("validation_status") == "ACCEPTED"
        and ai_decision == "SUGGEST_CHANGE"
        and suggested_category
        and suggested_category != deterministic_category
    ):
        diagnostic_flags.append("AI_DISAGREEMENT")

    result = {
        "Row Index": row_index,
        "Narration": row.get("Narration", ""),
        "Old Category": row.get("Old Category", ""),
        "Category": deterministic_category,
        "Confidence": payload["deterministic"]["confidence"],
        "Diagnostic Flags": " | ".join(diagnostic_flags),
        "AI Decision": accepted.get("decision", "INVALID"),
        "AI Suggested Category": accepted.get("suggested_category", ""),
        "Refinement Type": accepted.get("refinement_type", ""),
        "AI Semantic Reason": accepted.get("semantic_reason", ""),
        "AI Rule Suggestion": accepted.get("recommended_deterministic_improvement", ""),
        "AI Missing Signal": accepted.get("missing_or_misread_signal", ""),
        "AI Confidence Advisory": accepted.get("ai_confidence_advisory", ""),
        "Validation Status": validation.get("validation_status", "REJECTED"),
        "Validation Errors": " | ".join(validation.get("validation_errors", [])),
    }

    log_entry = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "semantic_payload": payload,
        "prompt": prompt,
        "raw_ai_response": raw_response,
        "extracted_ai_response": extracted_response,
        "parsed_ai_response": parsed_response,
        "validation": validation,
        "refinement_result": result,
        "model_metadata": {
            "provider": provider,
            "model": model,
            "base_url": base_url,
        },
    }
    append_refinement_log(log_entry, log_path=log_path)

    return result


def refine_transactions(
    processed_df,
    threshold=REVIEW_CONFIDENCE_THRESHOLD,
    model=DEFAULT_OLLAMA_MODEL,
    base_url=DEFAULT_OLLAMA_URL,
    generate_func=None,
    log_path=DEFAULT_LOG_PATH,
    include_old_category_disagreement=True,
    max_rows=None,
    provider="ollama",
):
    selected = select_rows_for_refinement(
        processed_df,
        threshold=threshold,
        include_old_category_disagreement=include_old_category_disagreement,
    )

    if max_rows:
        selected = selected.head(max_rows)

    results = []

    for row_index, row in selected.iterrows():
        results.append(
            refine_row(
                row,
                row_index=row_index,
                model=model,
                base_url=base_url,
                generate_func=generate_func,
                log_path=log_path,
                provider=provider,
            )
        )

    return results
