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
    APPROVED_CATEGORY_SET,
    CATEGORY_DEFINITION_VERSION,
    CATEGORY_DEFINITIONS,
    CATEGORY_FAMILIES,
    REVIEW_CONFIDENCE_THRESHOLD,
    TAXONOMY_VERSION,
)


DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_LOG_PATH = "output/ai_refinement_logs.jsonl"
DEFAULT_LOG_DETAIL = "summary"
DEFAULT_ROUTING_POLICY = "balanced"
ROUTING_POLICIES = {
    "strict",
    "balanced",
    "exploratory",
}
LOG_DETAIL_LEVELS = {
    "none",
    "summary",
    "audit",
}
SKIPPED_LOG_MODES = {
    "none",
    "summary",
    "rows",
}


GENERIC_TRANSFER_CATEGORIES = {
    "ELECTRONIC FUND TRANSFER",
    "TRANSFER IN",
    "TRANSFER OUT",
}


PAYMENT_CHANNEL_ROLES = {
    "payment_channel",
    "payment_processor",
    "wallet",
}


BACKGROUND_RAIL_CONFLICTS = {
    "rail_entity_ambiguity",
    "competing_hypotheses",
}


INTENT_CATEGORY_HINTS = {
    "reversal": {"REFUND OR REVERSAL"},
    "bounce": CATEGORY_FAMILIES["bounce"],
    "charge": {"BANK CHARGES"},
    "salary": {"SALARY", "SALARY PAID", "SALARY RECEIVED"},
    "tax": {"TAX"},
    "interest": {"INTEREST"},
    "investment": {"INVESTMENTS"},
    "insurance": {"INSURANCE"},
    "recharge": {"RECHARGE"},
    "travel": {"TRAVEL"},
    "utility": {"UTILITY"},
    "loan": {"LOAN"},
    "fuel": {"FUEL"},
    "fixed_deposit": {"FIXED DEPOSIT"},
    "auto_sweep": {"AUTO SWEEP"},
    "credit_card_payment": {"CREDIT CARD PAYMENT"},
    "demand_draft": {"DEMAND DRAFT"},
    "direct_debit": {"LOAN", "TRANSFER OUT", "ACH BOUNCED CHARGES", "ECS BOUNCED CHARGES"},
}


RAIL_CATEGORY_HINTS = {
    "UPI": {"ELECTRONIC FUND TRANSFER", "PAYMENT GATEWAY"},
    "IMPS": {"ELECTRONIC FUND TRANSFER", "IMPS BOUNCE", "IMPS BOUNCE CHARGES"},
    "NEFT": {"ELECTRONIC FUND TRANSFER", "NEFT BOUNCE"},
    "RTGS": {"ELECTRONIC FUND TRANSFER", "RTGS BOUNCE"},
    "ACH": {"LOAN", "TRANSFER OUT", "ACH BOUNCED CHARGES"},
    "ECS": {"LOAN", "TRANSFER OUT", "ECS BOUNCED CHARGES"},
    "NACH": {"LOAN", "TRANSFER OUT", "ECS BOUNCED CHARGES"},
    "ATM": {"ATM DEPOSIT", "ATM WITHDRAWAL", "CASH DEPOSIT", "CASH WITHDRAWAL"},
    "CHEQUE": CATEGORY_FAMILIES["cheque"],
}


BUSINESS_COUNTERPARTY_TERMS = {
    "AGENCY",
    "AGENCIES",
    "BAKERY",
    "CAFE",
    "COMPANY",
    "CORP",
    "ELECTRIC",
    "ELECTRONIC",
    "ENTERPRISE",
    "ENTERPRISES",
    "FASHION",
    "FILLING",
    "FILLINGS",
    "FOOD",
    "FOODS",
    "HOTEL",
    "INDIA",
    "LLP",
    "LTD",
    "MART",
    "MEDICAL",
    "PAYMENT",
    "PAYMEN",
    "PETROL",
    "PHARMA",
    "PVT",
    "RESTAURANT",
    "RETAIL",
    "SERVICE",
    "SERVICES",
    "SHOP",
    "SOLUTIONS",
    "SONS",
    "STORE",
    "SUPER",
    "TRADERS",
    "TRADING",
    "TRAVEL",
}


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


def _float_value(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean_value(value):
    if value in (None, "", "UNKNOWN"):
        return ""

    return str(value).strip()


def _normalize_policy(routing_policy):
    if routing_policy in ROUTING_POLICIES:
        return routing_policy

    return DEFAULT_ROUTING_POLICY


def _has_old_category_disagreement(row, include_old_category_disagreement=True):
    if not include_old_category_disagreement or "Old Category" not in row:
        return False

    old_category = row.get("Old Category")
    category = row.get("Category")

    return old_category not in (None, "") and old_category != category


def _candidate_categories(row):
    return {
        candidate["category"]
        for candidate in _top_candidates(row, limit=5)
        if candidate.get("category")
    }


def _business_like_counterparty(counterparty):
    text = _clean_value(counterparty).upper()

    if not text:
        return False

    tokens = {
        token
        for token in re.split(r"[^A-Z0-9]+", text)
        if token
    }

    if tokens.intersection(BUSINESS_COUNTERPARTY_TERMS):
        return True

    compact = re.sub(r"[^A-Z0-9]+", "", text)
    return any(term in compact for term in BUSINESS_COUNTERPARTY_TERMS if len(term) >= 5)


def _route_context(row, threshold, include_old_category_disagreement, routing_policy):
    policy = _normalize_policy(routing_policy)
    category = _clean_value(row.get("Category")) or "UNKNOWN"
    confidence = _float_value(row.get("Confidence"), default=0.0)
    conflicts = set(_major_conflicts(row))
    candidates = _candidate_categories(row)
    intent_tags = set(_pipe_values(row.get("Intent Tags", "")))
    movement_tags = set(_pipe_values(row.get("Movement Tags", "")))
    specific_movement_tags = movement_tags - {"manual_transfer"}
    entity_category = _clean_value(row.get("Entity Type"))
    entity_role = _clean_value(row.get("Entity Role"))
    entity_confidence = _float_value(row.get("Entity Confidence"), default=0.0)
    merchant = _clean_value(row.get("Merchant"))
    counterparty = _clean_value(row.get("Entity Name"))
    parse_quality = _clean_value(row.get("Parse Quality")) or "LOW"
    parser_rule = _clean_value(row.get("Parser Rule"))
    bank_family = _clean_value(row.get("Bank Family"))
    review_required = bool(row.get("Review Required", False))

    known_entity = bool(entity_category and merchant)
    strong_known_entity = known_entity and entity_confidence >= 0.75
    payment_channel_only = (
        entity_role in PAYMENT_CHANNEL_ROLES
        and not intent_tags
        and not specific_movement_tags
    )
    parser_gap = parse_quality == "LOW" or parser_rule == "NO_PARSER_MATCH"
    old_category_disagreement = _has_old_category_disagreement(
        row,
        include_old_category_disagreement=include_old_category_disagreement,
    )
    possible_entity_gap = (
        not known_entity
        and _business_like_counterparty(counterparty)
    )
    entity_gap_needs_ai = (
        possible_entity_gap
        and (
            category in GENERIC_TRANSFER_CATEGORIES
            or confidence < threshold
            or review_required
            or bool(conflicts)
            or old_category_disagreement
            or policy == "exploratory"
        )
    )
    has_meaningful_semantics = any(
        [
            known_entity,
            bool(intent_tags),
            bool(specific_movement_tags),
            bool(bank_family),
            possible_entity_gap,
        ]
    )
    generic_transfer_only = (
        category in GENERIC_TRANSFER_CATEGORIES
        and not has_meaningful_semantics
    )
    known_entity_rail_background = (
        strong_known_entity
        and category not in GENERIC_TRANSFER_CATEGORIES
        and "ELECTRONIC FUND TRANSFER" in candidates
        and conflicts
        and conflicts.issubset(BACKGROUND_RAIL_CONFLICTS)
    )
    substantive_competition = (
        bool(conflicts.intersection({"competing_hypotheses", "entity_category_disagreement"}))
        and not known_entity_rail_background
        and not payment_channel_only
        and has_meaningful_semantics
    )
    weak_evidence_with_context = (
        confidence < threshold
        and has_meaningful_semantics
        and not generic_transfer_only
        and not payment_channel_only
    )
    has_routing_trigger = any(
        [
            confidence < threshold,
            review_required,
            bool(conflicts),
            old_category_disagreement,
            entity_gap_needs_ai and policy in {"balanced", "exploratory"},
        ]
    )

    return {
        "policy": policy,
        "category": category,
        "confidence": confidence,
        "conflicts": conflicts,
        "candidates": candidates,
        "intent_tags": intent_tags,
        "specific_movement_tags": specific_movement_tags,
        "entity_category": entity_category,
        "entity_role": entity_role,
        "known_entity": known_entity,
        "strong_known_entity": strong_known_entity,
        "payment_channel_only": payment_channel_only,
        "parser_gap": parser_gap,
        "old_category_disagreement": old_category_disagreement,
        "possible_entity_gap": possible_entity_gap,
        "entity_gap_needs_ai": entity_gap_needs_ai,
        "has_meaningful_semantics": has_meaningful_semantics,
        "generic_transfer_only": generic_transfer_only,
        "known_entity_rail_background": known_entity_rail_background,
        "substantive_competition": substantive_competition,
        "weak_evidence_with_context": weak_evidence_with_context,
        "has_routing_trigger": has_routing_trigger,
    }


def route_row_for_refinement(
    row,
    threshold=REVIEW_CONFIDENCE_THRESHOLD,
    include_old_category_disagreement=True,
    routing_policy=DEFAULT_ROUTING_POLICY,
):
    context = _route_context(
        row,
        threshold=threshold,
        include_old_category_disagreement=include_old_category_disagreement,
        routing_policy=routing_policy,
    )
    policy = context["policy"]

    if not context["has_routing_trigger"]:
        return {
            "eligible": False,
            "routing_reason": "",
            "skip_reason": "NO_REVIEW_SIGNAL",
            "routing_policy": policy,
        }

    if context["known_entity_rail_background"] and policy != "exploratory":
        return {
            "eligible": False,
            "routing_reason": "",
            "skip_reason": "KNOWN_ENTITY_RAIL_BACKGROUND",
            "routing_policy": policy,
        }

    if context["payment_channel_only"] and policy != "exploratory":
        return {
            "eligible": False,
            "routing_reason": "",
            "skip_reason": "PAYMENT_CHANNEL_ONLY",
            "routing_policy": policy,
        }

    if context["generic_transfer_only"]:
        return {
            "eligible": False,
            "routing_reason": "",
            "skip_reason": "GENERIC_TRANSFER_ONLY",
            "routing_policy": policy,
        }

    if context["possible_entity_gap"]:
        if policy == "strict" and not (
            context["substantive_competition"] or context["parser_gap"]
        ):
            return {
                "eligible": False,
                "routing_reason": "",
                "skip_reason": "ENTITY_GAP_STRICT_POLICY",
                "routing_policy": policy,
            }

        return {
            "eligible": True,
            "routing_reason": "ENTITY_RULE_GAP",
            "skip_reason": "",
            "routing_policy": policy,
        }

    if context["substantive_competition"]:
        return {
            "eligible": True,
            "routing_reason": "SUBSTANTIVE_GROUP_AMBIGUITY",
            "skip_reason": "",
            "routing_policy": policy,
        }

    if context["parser_gap"] and context["has_meaningful_semantics"]:
        return {
            "eligible": True,
            "routing_reason": "PARSER_GAP",
            "skip_reason": "",
            "routing_policy": policy,
        }

    if context["weak_evidence_with_context"]:
        return {
            "eligible": True,
            "routing_reason": "WEAK_DETERMINISTIC_EVIDENCE",
            "skip_reason": "",
            "routing_policy": policy,
        }

    if context["old_category_disagreement"] and context["has_meaningful_semantics"]:
        return {
            "eligible": True,
            "routing_reason": "OLD_CATEGORY_DISAGREEMENT",
            "skip_reason": "",
            "routing_policy": policy,
        }

    if policy == "exploratory" and context["payment_channel_only"]:
        return {
            "eligible": True,
            "routing_reason": "PAYMENT_CHANNEL_AMBIGUITY",
            "skip_reason": "",
            "routing_policy": policy,
        }

    return {
        "eligible": False,
        "routing_reason": "",
        "skip_reason": "NO_ACTIONABLE_AI_CONTEXT",
        "routing_policy": policy,
    }


def annotate_refinement_routing(
    df,
    threshold=REVIEW_CONFIDENCE_THRESHOLD,
    include_old_category_disagreement=True,
    routing_policy=DEFAULT_ROUTING_POLICY,
):
    routed = df.copy()
    routing_results = routed.apply(
        lambda row: route_row_for_refinement(
            row,
            threshold=threshold,
            include_old_category_disagreement=include_old_category_disagreement,
            routing_policy=routing_policy,
        ),
        axis=1,
    )

    routed["AI Routing Policy"] = routing_results.apply(lambda result: result["routing_policy"])
    routed["AI Refinement Eligible"] = routing_results.apply(lambda result: result["eligible"])
    routed["AI Routing Reason"] = routing_results.apply(lambda result: result["routing_reason"])
    routed["AI Skip Reason"] = routing_results.apply(lambda result: result["skip_reason"])

    return routed


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


def should_refine_row(
    row,
    threshold=REVIEW_CONFIDENCE_THRESHOLD,
    include_old_category_disagreement=True,
    routing_policy=DEFAULT_ROUTING_POLICY,
):
    return route_row_for_refinement(
        row,
        threshold=threshold,
        include_old_category_disagreement=include_old_category_disagreement,
        routing_policy=routing_policy,
    )["eligible"]


def select_rows_for_refinement(
    df,
    threshold=REVIEW_CONFIDENCE_THRESHOLD,
    include_old_category_disagreement=True,
    routing_policy=DEFAULT_ROUTING_POLICY,
):
    routed = annotate_refinement_routing(
        df,
        threshold=threshold,
        include_old_category_disagreement=include_old_category_disagreement,
        routing_policy=routing_policy,
    )

    return routed[routed["AI Refinement Eligible"]].copy()


def _add_category_hint(categories, category):
    category = _clean_value(category)

    if category in CATEGORY_DEFINITIONS:
        categories.add(category)


def _category_definitions_for_row(row):
    categories = set()
    direction = _clean_value(row.get("Direction"))
    rail = _clean_value(row.get("Mode"))
    entity_category = _clean_value(row.get("Entity Type"))
    counterparty = _clean_value(row.get("Entity Name"))
    routing_reason = _clean_value(row.get("AI Routing Reason"))
    intent_tags = set(_pipe_values(row.get("Intent Tags", "")))
    movement_tags = set(_pipe_values(row.get("Movement Tags", "")))
    possible_entity_gap = (
        not entity_category
        and _business_like_counterparty(counterparty)
    )

    _add_category_hint(categories, row.get("Category"))
    _add_category_hint(categories, entity_category)

    for candidate in _top_candidates(row, limit=5):
        _add_category_hint(categories, candidate.get("category"))

    for category in RAIL_CATEGORY_HINTS.get(rail, set()):
        _add_category_hint(categories, category)

    for tag in intent_tags:
        for category in INTENT_CATEGORY_HINTS.get(tag, set()):
            _add_category_hint(categories, category)

    if direction == "IN":
        _add_category_hint(categories, "TRANSFER IN")
    elif direction == "OUT":
        _add_category_hint(categories, "TRANSFER OUT")
    else:
        _add_category_hint(categories, "ELECTRONIC FUND TRANSFER")

    if "debit_card" in movement_tags:
        _add_category_hint(
            categories,
            "DEBIT CARD TRANSFER IN" if direction == "IN" else "DEBIT CARD TRANSFER OUT",
        )

    if "cash" in movement_tags:
        _add_category_hint(categories, "CASH DEPOSIT")
        _add_category_hint(categories, "CASH WITHDRAWAL")

    if "cheque" in movement_tags:
        for category in CATEGORY_FAMILIES["cheque"]:
            _add_category_hint(categories, category)

    if (
        routing_reason in {"ENTITY_RULE_GAP", "PARSER_GAP", "WEAK_DETERMINISTIC_EVIDENCE"}
        or possible_entity_gap
    ):
        for category in CATEGORY_FAMILIES["generic_transfer"]:
            _add_category_hint(categories, category)

        if entity_category in {"UNKNOWN", ""}:
            for category in CATEGORY_FAMILIES["merchant_intent"]:
                _add_category_hint(categories, category)

    if not categories:
        for category in CATEGORY_FAMILIES["generic_transfer"]:
            _add_category_hint(categories, category)

    return {
        category: CATEGORY_DEFINITIONS[category]
        for category in sorted(categories)
    }


def build_semantic_payload(row, row_index=None):
    category_definitions = _category_definitions_for_row(row)
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
            "ai_refinement_eligible": bool(row.get("AI Refinement Eligible", False)),
            "ai_routing_policy": row.get("AI Routing Policy", DEFAULT_ROUTING_POLICY),
            "ai_routing_reason": row.get("AI Routing Reason", ""),
            "ai_skip_reason": row.get("AI Skip Reason", ""),
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
        "allowed_categories": sorted(category_definitions),
        "category_definitions": category_definitions,
    }

    return payload


def build_refinement_prompt(payload):
    instruction = {
        "task": "Advisory validation of deterministic transaction categorization.",
        "rules": [
            "Return one compact JSON object only.",
            "Use only semantic_payload.allowed_categories for suggested_category.",
            "Use SUGGEST_CHANGE only when the payload supports a safe category change now.",
            "Use NEEDS_DETERMINISTIC_FIX when parser/entity/evidence context is weak and needs engine work before a safe category change.",
            "Use INSUFFICIENT_EVIDENCE when neither a category change nor a deterministic fix is supported.",
            "Use NO_CHANGE when the deterministic category is semantically correct.",
            "No markdown, prose, chain-of-thought, or wrapper objects.",
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
            "decision": "NO_CHANGE, SUGGEST_CHANGE, NEEDS_DETERMINISTIC_FIX, or INSUFFICIENT_EVIDENCE",
            "suggested_category": "One category from semantic_payload.allowed_categories",
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
        separators=(",", ":"),
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


def _default_engine_fix(payload, validation_errors=None):
    summary = payload.get("semantic_summary", {})
    deterministic = payload.get("deterministic", {})
    routing_reason = deterministic.get("ai_routing_reason", "")
    diagnostic_flags = set(payload.get("diagnostic_flags", []))
    errors = validation_errors or []

    if any("requires rail" in error for error in errors):
        return "Add or fix rail parser evidence before accepting this category."

    if any("requires direction" in error for error in errors):
        return "Fix movement direction evidence before accepting this category."

    if routing_reason == "ENTITY_RULE_GAP" or summary.get("entity_category") == "UNKNOWN":
        return "Add counterparty to entity registry or merchant/category mapping."

    if (
        routing_reason == "PARSER_GAP"
        or "SEMANTIC_EXTRACTION_FAILURE" in diagnostic_flags
        or summary.get("protocol_family") == "UNKNOWN"
    ):
        return "Add parser coverage for this narration family."

    if routing_reason == "WEAK_DETERMINISTIC_EVIDENCE":
        return "Strengthen deterministic evidence weights or semantic signals."

    return "Review deterministic parser/entity evidence before changing category."


def _coerce_legacy_ai_output(ai_output, payload):
    if not isinstance(ai_output, dict):
        return ai_output

    normalized = dict(ai_output)
    deterministic_category = payload.get("deterministic", {}).get("category")
    decision = normalized.get("decision")
    suggested_category = normalized.get("suggested_category") or deterministic_category

    if suggested_category in (None, ""):
        suggested_category = deterministic_category

    normalized["suggested_category"] = suggested_category

    if decision == "SUGGEST_CHANGE" and suggested_category == deterministic_category:
        normalized["decision"] = "NEEDS_DETERMINISTIC_FIX"

        if not normalized.get("semantic_reason"):
            normalized["semantic_reason"] = "Deterministic category has weak supporting evidence."

        if not normalized.get("recommended_deterministic_improvement"):
            normalized["recommended_deterministic_improvement"] = _default_engine_fix(payload)

    if normalized.get("decision") in {"NEEDS_DETERMINISTIC_FIX", "INSUFFICIENT_EVIDENCE"}:
        if normalized.get("suggested_category") not in APPROVED_CATEGORY_SET:
            normalized["suggested_category"] = deterministic_category

        if not normalized.get("recommended_deterministic_improvement"):
            normalized["recommended_deterministic_improvement"] = _default_engine_fix(payload)

    return normalized


def _salvage_advisory_validation(ai_output, payload, validation):
    if validation.get("validation_status") != "REJECTED":
        return validation

    if not isinstance(ai_output, dict):
        return validation

    suggested_category = ai_output.get("suggested_category")

    if suggested_category not in APPROVED_CATEGORY_SET:
        return validation

    validation_errors = validation.get("validation_errors", [])
    can_preserve_as_advisory = any(
        (
            "requires rail" in error
            or "requires direction" in error
            or "requires one of" in error
            or "SUGGEST_CHANGE requires suggested_category to differ" in error
        )
        for error in validation_errors
    )

    if not can_preserve_as_advisory:
        return validation

    advisory_output = dict(ai_output)
    advisory_output["decision"] = "NEEDS_DETERMINISTIC_FIX"

    if not advisory_output.get("recommended_deterministic_improvement"):
        advisory_output["recommended_deterministic_improvement"] = _default_engine_fix(
            payload,
            validation_errors=validation_errors,
        )

    if not advisory_output.get("semantic_reason"):
        advisory_output["semantic_reason"] = "Potential category signal needs deterministic support."

    advisory_validation = validate_ai_output(advisory_output, payload)
    advisory_validation["validation_warnings"] = (
        advisory_validation.get("validation_warnings", []) + validation_errors
    )

    return advisory_validation


def _ai_outcome(validation, ai_output):
    if validation.get("validation_status") != "ACCEPTED":
        return "INVALID_RESPONSE"

    decision = ai_output.get("decision")

    if decision == "SUGGEST_CHANGE":
        return "CATEGORY_CHANGE_SUGGESTED"

    if decision == "NO_CHANGE":
        return "CATEGORY_CONFIRMED"

    if decision == "NEEDS_DETERMINISTIC_FIX":
        return "ENGINE_FIX_NEEDED"

    if decision == "INSUFFICIENT_EVIDENCE":
        return "INSUFFICIENT_EVIDENCE"

    return "INVALID_RESPONSE"


def _ai_finding(validation, accepted, parsed_response):
    source = accepted if accepted else parsed_response if isinstance(parsed_response, dict) else {}

    if source.get("semantic_reason"):
        return source["semantic_reason"]

    errors = validation.get("validation_errors", [])

    if errors:
        return errors[0]

    return ""


def _ai_proposed_action(validation, accepted, parsed_response, payload):
    source = accepted if accepted else parsed_response if isinstance(parsed_response, dict) else {}

    if source.get("recommended_deterministic_improvement"):
        return source["recommended_deterministic_improvement"]

    warnings = validation.get("validation_warnings", [])
    errors = validation.get("validation_errors", [])

    if warnings or errors:
        return _default_engine_fix(payload, validation_errors=warnings + errors)

    return ""


def call_ollama(prompt, model=DEFAULT_OLLAMA_MODEL, base_url=DEFAULT_OLLAMA_URL, timeout=120):
    response = requests.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "num_predict": 256,
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


def _normalize_log_detail(log_detail):
    if log_detail in LOG_DETAIL_LEVELS:
        return log_detail

    return DEFAULT_LOG_DETAIL


def _normalize_skipped_log_mode(log_skipped):
    if log_skipped is True:
        return "summary"

    if log_skipped is False:
        return "none"

    if log_skipped in SKIPPED_LOG_MODES:
        return log_skipped

    return "summary"


def log_skipped_refinement_summary(
    skipped,
    log_path=DEFAULT_LOG_PATH,
    provider="ollama",
    model=DEFAULT_OLLAMA_MODEL,
    base_url=DEFAULT_OLLAMA_URL,
):
    if skipped.empty:
        return {}

    skip_counts = {}
    sample_rows = []

    for row_index, row in skipped.iterrows():
        reason = row.get("AI Skip Reason", "NO_ACTIONABLE_AI_CONTEXT")
        skip_counts[reason] = skip_counts.get(reason, 0) + 1

        if len(sample_rows) < 10:
            sample_rows.append(
                {
                    "Row Index": row_index,
                    "Category": row.get("Category", "UNKNOWN"),
                    "Confidence": row.get("Confidence", 0.0),
                    "AI Skip Reason": reason,
                }
            )

    result = {
        "skipped_count": int(len(skipped)),
        "skip_counts": skip_counts,
        "sample_rows": sample_rows,
    }

    append_refinement_log(
        {
            "event_type": "AI_REFINEMENT_SKIPPED_SUMMARY",
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "refinement_result": result,
            "model_metadata": {
                "provider": provider,
                "model": model,
                "base_url": base_url,
            },
        },
        log_path=log_path,
    )

    return result


def log_skipped_refinement_row(
    row,
    row_index=None,
    log_path=DEFAULT_LOG_PATH,
    provider="ollama",
    model=DEFAULT_OLLAMA_MODEL,
    base_url=DEFAULT_OLLAMA_URL,
):
    result = {
        "Row Index": row_index,
        "Narration": row.get("Narration", ""),
        "Category": row.get("Category", "UNKNOWN"),
        "Confidence": row.get("Confidence", 0.0),
        "Review Required": bool(row.get("Review Required", False)),
        "AI Routing Policy": row.get("AI Routing Policy", DEFAULT_ROUTING_POLICY),
        "AI Refinement Eligible": False,
        "AI Routing Reason": row.get("AI Routing Reason", ""),
        "AI Skip Reason": row.get("AI Skip Reason", "NO_ACTIONABLE_AI_CONTEXT"),
    }

    append_refinement_log(
        {
            "event_type": "AI_REFINEMENT_SKIPPED",
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "row_index": row_index,
            "refinement_result": result,
            "model_metadata": {
                "provider": provider,
                "model": model,
                "base_url": base_url,
            },
        },
        log_path=log_path,
    )

    return result


def _append_attempt_log(
    payload,
    prompt,
    raw_response,
    extracted_response,
    parsed_response,
    validation,
    result,
    log_path,
    provider,
    model,
    base_url,
    log_detail,
):
    detail = _normalize_log_detail(log_detail)

    if detail == "none":
        return

    log_entry = {
        "event_type": "AI_REFINEMENT_ATTEMPTED",
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "row_index": result.get("Row Index"),
        "prompt_chars": len(prompt),
        "category_definition_count": len(payload.get("category_definitions", {})),
        "parsed_ai_response": parsed_response,
        "validation": validation,
        "refinement_result": result,
        "model_metadata": {
            "provider": provider,
            "model": model,
            "base_url": base_url,
        },
    }

    if detail == "audit":
        log_entry.update(
            {
                "semantic_payload": payload,
                "prompt": prompt,
                "raw_ai_response": raw_response,
                "extracted_ai_response": extracted_response,
            }
        )

    append_refinement_log(log_entry, log_path=log_path)


def refine_row(
    row,
    row_index=None,
    model=DEFAULT_OLLAMA_MODEL,
    base_url=DEFAULT_OLLAMA_URL,
    generate_func=None,
    log_path=DEFAULT_LOG_PATH,
    provider="ollama",
    log_detail=DEFAULT_LOG_DETAIL,
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
        parsed_response = _coerce_legacy_ai_output(parsed_response, payload)
        validation = validate_ai_output(parsed_response, payload)
        validation = _salvage_advisory_validation(parsed_response, payload, validation)
    except Exception as exc:
        validation = {
            "validation_status": "REJECTED",
            "validation_errors": [str(exc)],
            "validation_warnings": [],
            "validator_version": "UNAVAILABLE",
            "validated_output": {},
        }

    accepted = validation.get("validated_output", {})
    deterministic_category = payload["deterministic"]["category"]
    parsed_for_display = parsed_response if isinstance(parsed_response, dict) else {}
    suggested_category = accepted.get("suggested_category", parsed_for_display.get("suggested_category", ""))
    ai_decision = accepted.get("decision", parsed_for_display.get("decision", "INVALID_RESPONSE"))
    ai_outcome = _ai_outcome(validation, accepted)
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
        "AI Routing Policy": payload["deterministic"]["ai_routing_policy"],
        "AI Refinement Eligible": payload["deterministic"]["ai_refinement_eligible"],
        "AI Routing Reason": payload["deterministic"]["ai_routing_reason"],
        "AI Skip Reason": payload["deterministic"]["ai_skip_reason"],
        "AI Outcome": ai_outcome,
        "AI Decision": ai_decision,
        "AI Suggested Category": suggested_category,
        "Refinement Type": accepted.get("refinement_type", parsed_for_display.get("refinement_type", "")),
        "AI Finding": _ai_finding(validation, accepted, parsed_response),
        "AI Proposed Action": _ai_proposed_action(validation, accepted, parsed_response, payload),
        "AI Semantic Reason": accepted.get("semantic_reason", parsed_for_display.get("semantic_reason", "")),
        "AI Rule Suggestion": accepted.get(
            "recommended_deterministic_improvement",
            parsed_for_display.get("recommended_deterministic_improvement", ""),
        ),
        "AI Missing Signal": accepted.get(
            "missing_or_misread_signal",
            parsed_for_display.get("missing_or_misread_signal", ""),
        ),
        "AI Confidence Advisory": accepted.get(
            "ai_confidence_advisory",
            parsed_for_display.get("ai_confidence_advisory", ""),
        ),
        "Validation Status": validation.get("validation_status", "REJECTED"),
        "Validation Errors": " | ".join(validation.get("validation_errors", [])),
        "Validation Warnings": " | ".join(validation.get("validation_warnings", [])),
    }

    _append_attempt_log(
        payload=payload,
        prompt=prompt,
        raw_response=raw_response,
        extracted_response=extracted_response,
        parsed_response=parsed_response,
        validation=validation,
        result=result,
        log_path=log_path,
        provider=provider,
        model=model,
        base_url=base_url,
        log_detail=log_detail,
    )

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
    routing_policy=DEFAULT_ROUTING_POLICY,
    log_skipped="summary",
    log_detail=DEFAULT_LOG_DETAIL,
):
    routed = annotate_refinement_routing(
        processed_df,
        threshold=threshold,
        include_old_category_disagreement=include_old_category_disagreement,
        routing_policy=routing_policy,
    )
    selected = routed[routed["AI Refinement Eligible"]].copy()

    if max_rows:
        selected = selected.head(max_rows)
        selected_indexes = set(selected.index)
        over_limit = routed[
            routed["AI Refinement Eligible"]
            & ~routed.index.isin(selected_indexes)
        ].copy()
        if not over_limit.empty:
            over_limit["AI Refinement Eligible"] = False
            over_limit["AI Routing Reason"] = ""
            over_limit["AI Skip Reason"] = "MAX_ROWS_LIMIT"

        skipped = routed[~routed.index.isin(selected_indexes)].copy()
        skipped.update(over_limit)
    else:
        skipped = routed[~routed["AI Refinement Eligible"]].copy()

    skipped_log_mode = _normalize_skipped_log_mode(log_skipped)

    if skipped_log_mode == "rows":
        for row_index, row in skipped.iterrows():
            log_skipped_refinement_row(
                row,
                row_index=row_index,
                log_path=log_path,
                provider=provider,
                model=model,
                base_url=base_url,
            )
    elif skipped_log_mode == "summary":
        log_skipped_refinement_summary(
            skipped,
            log_path=log_path,
            provider=provider,
            model=model,
            base_url=base_url,
        )

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
                log_detail=log_detail,
            )
        )

    return results
