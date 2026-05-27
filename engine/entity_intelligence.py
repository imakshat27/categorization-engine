from engine.entity_registry import ENTITY_REGISTRY
from engine.matcher import clean_entity_text, token_match


def detect_entity_type(entity_name):
    text = clean_entity_text(entity_name)
    best = None

    for entity in ENTITY_REGISTRY:
        for alias in entity["aliases"]:
            match = token_match(
                alias,
                text,
                rule_name=f"ENTITY_{entity['canonical']}",
                source="entity",
            )

            if not match:
                continue

            if best is None or entity["confidence"] > best["entity_confidence"]:
                best = {
                    "entity_type": entity["category"],
                    "entity_confidence": entity["confidence"],
                    "matched_entity_rule": entity["canonical"],
                    "entity_role": entity["role"],
                    "entity_ambiguity": entity["ambiguity"],
                }

    if best:
        return best

    return {
        "entity_type": "UNKNOWN",
        "entity_confidence": 0.0,
        "matched_entity_rule": "NO_ENTITY_MATCH",
        "entity_role": "UNKNOWN",
        "entity_ambiguity": "UNKNOWN",
    }

