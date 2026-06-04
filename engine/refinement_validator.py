from engine.refinement_contracts import (
    AI_DECISIONS,
    REFINEMENT_TYPES,
    REQUIRED_AI_FIELDS,
)
from engine.taxonomy import (
    APPROVED_CATEGORY_SET,
    CATEGORY_COMPATIBILITY_RULES,
    VALIDATOR_VERSION,
)


def _values(value):
    if value in (None, "", "UNKNOWN"):
        return set()

    if isinstance(value, str):
        return {
            item.strip()
            for item in value.split("|")
            if item.strip()
        }

    if isinstance(value, (list, tuple, set)):
        return {
            str(item).strip()
            for item in value
            if str(item).strip()
        }

    return {str(value).strip()}


def _semantic_summary(payload):
    return payload.get("semantic_summary", {})


def _compatible_with_payload(category, payload):
    rules = CATEGORY_COMPATIBILITY_RULES.get(category)

    if not rules:
        return True, []

    summary = _semantic_summary(payload)
    errors = []

    allowed_directions = rules.get("direction")
    direction = summary.get("direction")

    if allowed_directions and direction not in allowed_directions:
        errors.append(
            f"{category} requires direction {sorted(allowed_directions)}, got {direction}"
        )

    allowed_rails = rules.get("rail")
    rail = summary.get("rail")

    if allowed_rails and rail not in allowed_rails:
        errors.append(
            f"{category} requires rail {sorted(allowed_rails)}, got {rail}"
        )

    for field, required_values in rules.get("requires_any", {}).items():
        available = _values(summary.get(field))

        if available and not available.intersection(required_values):
            errors.append(
                f"{category} requires one of {sorted(required_values)} in {field}, got {sorted(available)}"
            )

    return not errors, errors


def validate_ai_output(ai_output, payload):
    errors = []
    warnings = []

    if not isinstance(ai_output, dict):
        return {
            "validation_status": "REJECTED",
            "validation_errors": ["AI output is not a JSON object"],
            "validation_warnings": [],
            "validator_version": VALIDATOR_VERSION,
            "validated_output": {},
        }

    missing_fields = sorted(REQUIRED_AI_FIELDS - set(ai_output))

    if missing_fields:
        errors.append(f"Missing required fields: {', '.join(missing_fields)}")

    decision = ai_output.get("decision")
    suggested_category = ai_output.get("suggested_category")
    refinement_type = ai_output.get("refinement_type")
    deterministic_category = payload.get("deterministic", {}).get("category")

    if decision not in AI_DECISIONS:
        errors.append(f"Invalid decision: {decision}")

    if suggested_category not in APPROVED_CATEGORY_SET:
        errors.append(f"Invalid suggested_category: {suggested_category}")

    if refinement_type not in REFINEMENT_TYPES:
        errors.append(f"Invalid refinement_type: {refinement_type}")

    if decision == "NO_CHANGE" and suggested_category != deterministic_category:
        errors.append(
            "NO_CHANGE requires suggested_category to equal deterministic category"
        )

    if decision == "SUGGEST_CHANGE" and suggested_category == deterministic_category:
        errors.append(
            "SUGGEST_CHANGE requires suggested_category to differ from deterministic category"
        )

    if decision == "SUGGEST_CHANGE" and suggested_category in APPROVED_CATEGORY_SET:
        compatible, compatibility_errors = _compatible_with_payload(
            suggested_category,
            payload,
        )

        if not compatible:
            errors.extend(compatibility_errors)
    elif (
        decision in {"NEEDS_DETERMINISTIC_FIX", "INSUFFICIENT_EVIDENCE"}
        and suggested_category in APPROVED_CATEGORY_SET
    ):
        compatible, compatibility_errors = _compatible_with_payload(
            suggested_category,
            payload,
        )

        if not compatible:
            warnings.extend(compatibility_errors)

    return {
        "validation_status": "REJECTED" if errors else "ACCEPTED",
        "validation_errors": errors,
        "validation_warnings": warnings,
        "validator_version": VALIDATOR_VERSION,
        "validated_output": ai_output if not errors else {},
    }
