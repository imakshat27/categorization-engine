SEMANTIC_PAYLOAD_VERSION = "2026-05-28.1"
PROMPT_TEMPLATE_VERSION = "2026-05-28.1"
AI_OUTPUT_SCHEMA_VERSION = "2026-05-28.1"
DETERMINISTIC_ENGINE_VERSION = "semantic-engine-2026-05-28.1"


AI_DECISIONS = {
    "NO_CHANGE",
    "SUGGEST_CHANGE",
}


REFINEMENT_TYPES = {
    "ENTITY_OVERRIDE",
    "AMBIGUITY_RESOLUTION",
    "PARSER_GAP",
    "WEAK_DETERMINISTIC_EVIDENCE",
    "NO_ISSUE_DETECTED",
}


DIAGNOSTIC_FLAGS = {
    "SEMANTIC_EXTRACTION_FAILURE",
    "ONTOLOGY_AMBIGUITY",
    "EVIDENCE_WEIGHT_WEAKNESS",
    "AI_DISAGREEMENT",
}


REQUIRED_AI_FIELDS = {
    "decision",
    "suggested_category",
    "refinement_type",
    "semantic_reason",
    "missing_or_misread_signal",
    "recommended_deterministic_improvement",
    "ai_confidence_advisory",
}

