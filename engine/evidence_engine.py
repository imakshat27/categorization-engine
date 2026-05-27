from engine.taxonomy import (
    APPROVED_CATEGORY_SET,
    CATEGORY_PRECEDENCE,
    CONFLICT_PENALTIES,
    FALLBACK_CATEGORY_BY_DIRECTION,
    PARSER_QUALITY_MULTIPLIER,
    RAIL_CATEGORIES,
    REVIEW_CONFIDENCE_THRESHOLD,
)


SOURCE_WEIGHTS = {
    "intent": 0.96,
    "entity": 0.82,
    "protocol": 0.84,
    "movement": 0.78,
    "instrument": 0.88,
    "bank_family": 0.78,
    "fallback": 0.38,
}


def _evidence(category, source, strength, reason, provenance, opposing=False):
    return {
        "category": category,
        "source": source,
        "strength": strength,
        "reason": reason,
        "provenance": provenance,
        "opposing": opposing,
    }


def _add(items, category, source, strength, reason, provenance, opposing=False):
    if category not in APPROVED_CATEGORY_SET:
        return

    items.append(
        _evidence(
            category=category,
            source=source,
            strength=strength,
            reason=reason,
            provenance=provenance,
            opposing=opposing,
        )
    )


def build_evidence(facts):
    evidence = []
    protocol = facts["protocol"]
    entity = facts["entity"]
    movement = facts["movement"]
    intent = facts["intent"]
    bank_family = facts["bank_family"]

    rail = protocol.get("rail", "UNKNOWN")
    direction = movement.get("direction", "UNKNOWN")
    intent_tags = set(intent.get("tags", []))
    movement_tags = set(movement.get("tags", []))
    family = bank_family.get("family", "UNKNOWN")

    if "reversal" in intent_tags:
        _add(
            evidence,
            "REFUND OR REVERSAL",
            "intent",
            0.98,
            "reversal_or_refund_intent",
            "intent.tags.reversal",
        )

    if "bounce" in intent_tags:
        charge_suffix = "charge" in intent_tags

        if rail == "IMPS":
            _add(
                evidence,
                "IMPS BOUNCE CHARGES" if charge_suffix else "IMPS BOUNCE",
                "intent",
                0.94,
                "imps_bounce_intent",
                "intent.tags.bounce + protocol.rail.IMPS",
            )
        elif rail == "NEFT":
            _add(evidence, "NEFT BOUNCE", "intent", 0.93, "neft_bounce_intent", "intent.tags.bounce + protocol.rail.NEFT")
        elif rail == "RTGS":
            _add(evidence, "RTGS BOUNCE", "intent", 0.93, "rtgs_bounce_intent", "intent.tags.bounce + protocol.rail.RTGS")
        elif rail in {"ECS", "NACH"}:
            _add(evidence, "ECS BOUNCED CHARGES", "intent", 0.93, "ecs_bounce_intent", "intent.tags.bounce + protocol.rail.ECS")
        elif rail == "ACH":
            _add(evidence, "ACH BOUNCED CHARGES", "intent", 0.93, "ach_bounce_intent", "intent.tags.bounce + protocol.rail.ACH")

        if "cheque" in movement_tags or rail == "CHEQUE":
            if intent.get("bounce_type") == "TECHNICAL":
                _add(evidence, "CHEQUE BOUNCE - TECHNICAL", "intent", 0.95, "technical_cheque_bounce", "intent.bounce_type.TECHNICAL")
            else:
                _add(evidence, "CHEQUE BOUNCE - NON TECHNICAL", "intent", 0.93, "non_technical_cheque_bounce", "intent.bounce_type.NON_TECHNICAL_OR_UNKNOWN")

    if "charge" in intent_tags or family == "BANK_CHARGE":
        _add(
            evidence,
            "BANK CHARGES",
            "intent",
            0.92,
            "bank_charge_intent",
            "intent.tags.charge",
        )

    if "salary" in intent_tags:
        if direction == "IN":
            _add(evidence, "SALARY RECEIVED", "intent", 0.93, "salary_credit", "intent.salary + movement.direction.IN")
        elif direction == "OUT":
            _add(evidence, "SALARY PAID", "intent", 0.90, "salary_debit", "intent.salary + movement.direction.OUT")
        else:
            _add(evidence, "SALARY", "intent", 0.82, "salary_unknown_direction", "intent.salary")

    simple_intents = {
        "tax": ("TAX", 0.92),
        "interest": ("INTEREST", 0.93),
        "investment": ("INVESTMENTS", 0.88),
        "insurance": ("INSURANCE", 0.86),
        "recharge": ("RECHARGE", 0.84),
        "travel": ("TRAVEL", 0.84),
        "utility": ("UTILITY", 0.80),
        "loan": ("LOAN", 0.88),
        "fuel": ("FUEL", 0.86),
        "fixed_deposit": ("FIXED DEPOSIT", 0.90),
        "auto_sweep": ("AUTO SWEEP", 0.90),
        "credit_card_payment": ("CREDIT CARD PAYMENT", 0.86),
        "demand_draft": ("DEMAND DRAFT", 0.86),
    }

    for tag, (category, strength) in simple_intents.items():
        if tag in intent_tags:
            _add(evidence, category, "intent", strength, f"{tag}_intent", f"intent.tags.{tag}")

    if family == "SWEEP_FIXED_DEPOSIT":
        _add(evidence, "FIXED DEPOSIT", "bank_family", 0.88, "sweep_fixed_deposit_family", "bank_family.SWEEP_FIXED_DEPOSIT")
    elif family == "KOTAK_PAYOUT":
        _add(evidence, "TRANSFER IN" if direction == "IN" else "TRANSFER OUT", "bank_family", 0.74, "kotak_payout_transfer_family", "bank_family.KOTAK_PAYOUT")
    elif family == "CENTRAL_BANK_CASH_RECEIPT":
        _add(evidence, "CASH DEPOSIT", "bank_family", 0.66, "cash_receipt_family", "bank_family.CENTRAL_BANK_CASH_RECEIPT")
    elif family == "CHEQUE_CLEARING":
        _add(evidence, "CHEQUE DEPOSIT" if direction == "IN" else "CHEQUE WITHDRAWAL", "bank_family", 0.78, "cheque_clearing_family", "bank_family.CHEQUE_CLEARING")
    elif family == "DIRECT_DEBIT":
        _add(evidence, "TRANSFER OUT", "bank_family", 0.62, "direct_debit_transfer_family", "bank_family.DIRECT_DEBIT")
    elif family == "MANUAL_BENEFICIARY_TRANSFER":
        _add(evidence, "TRANSFER OUT", "bank_family", 0.64, "manual_beneficiary_transfer_family", "bank_family.MANUAL_BENEFICIARY_TRANSFER")

    if "atm" in movement_tags:
        _add(
            evidence,
            "ATM DEPOSIT" if direction == "IN" else "ATM WITHDRAWAL",
            "instrument",
            0.88,
            "atm_movement",
            "movement.tags.atm",
        )

    if "cheque" in movement_tags and "bounce" not in intent_tags:
        if "cash" in movement_tags and direction == "OUT":
            _add(evidence, "CHEQUE CASH WITHDRAWAL", "instrument", 0.88, "cheque_cash_withdrawal", "movement.cheque + movement.cash")
        elif direction == "IN":
            _add(evidence, "CHEQUE DEPOSIT", "instrument", 0.78, "cheque_deposit", "movement.cheque + direction.IN")
        elif direction == "OUT":
            _add(evidence, "CHEQUE WITHDRAWAL", "instrument", 0.78, "cheque_withdrawal", "movement.cheque + direction.OUT")

    if "cash" in movement_tags and "cheque" not in movement_tags:
        if direction == "IN" or "deposit" in movement_tags:
            _add(evidence, "CASH DEPOSIT", "movement", 0.88, "cash_deposit", "movement.cash + deposit/direction.IN")
        elif direction == "OUT" or "withdrawal" in movement_tags:
            _add(evidence, "CASH WITHDRAWAL", "movement", 0.86, "cash_withdrawal", "movement.cash + withdrawal/direction.OUT")

    if "debit_card" in movement_tags:
        _add(
            evidence,
            "DEBIT CARD TRANSFER IN" if direction == "IN" else "DEBIT CARD TRANSFER OUT",
            "instrument",
            0.76,
            "debit_card_transfer",
            "movement.tags.debit_card",
        )

    if entity.get("category") != "UNKNOWN":
        role = entity.get("role")
        category = entity["category"]
        strength = entity.get("confidence", 0.0)

        if role == "payment_channel":
            strength *= 0.55
        elif role == "payment_processor":
            strength *= 1.05
        elif role == "wallet":
            strength *= 0.90

        _add(
            evidence,
            category,
            "entity",
            strength,
            f"entity_{role}",
            f"entity.{entity.get('canonical')}",
        )

    if rail in RAIL_CATEGORIES:
        _add(
            evidence,
            RAIL_CATEGORIES[rail],
            "protocol",
            0.82,
            "generic_rail_transfer",
            f"protocol.rail.{rail}",
        )

    if "manual_transfer" in movement_tags:
        _add(
            evidence,
            "TRANSFER IN" if direction == "IN" else "TRANSFER OUT",
            "movement",
            0.80,
            "manual_transfer_movement",
            "movement.tags.manual_transfer",
        )

    if not evidence:
        _add(
            evidence,
            FALLBACK_CATEGORY_BY_DIRECTION.get(direction, "ELECTRONIC FUND TRANSFER"),
            "fallback",
            0.34,
            "weak_directional_fallback",
            f"movement.direction.{direction}",
        )

    return evidence


def _combined_score(evidence_items):
    score = 0.0

    for item in evidence_items:
        contribution = item["strength"] * SOURCE_WEIGHTS.get(item["source"], 0.5)
        contribution = max(0.0, min(contribution, 0.99))
        score = 1 - ((1 - score) * (1 - contribution))

    return score


def _rank_candidates(evidence):
    grouped = {}

    for item in evidence:
        grouped.setdefault(item["category"], []).append(item)

    candidates = []

    for category, items in grouped.items():
        score = _combined_score(items)
        candidates.append(
            {
                "category": category,
                "score": score,
                "evidence": items,
                "precedence": CATEGORY_PRECEDENCE.get(category, 0),
            }
        )

    candidates.sort(
        key=lambda candidate: (
            candidate["score"],
            candidate["precedence"],
        ),
        reverse=True,
    )

    return candidates


def _detect_conflicts(facts, candidates):
    conflicts = []
    movement_tags = set(facts["movement"].get("tags", []))
    protocol_rail = facts["protocol"].get("rail", "UNKNOWN")
    entity_category = facts["entity"].get("category", "UNKNOWN")
    parser_quality = facts["protocol"].get("parse_quality", "LOW")

    if {"deposit", "withdrawal"}.issubset(movement_tags):
        conflicts.append("deposit_withdrawal_conflict")

    if candidates:
        top = candidates[0]
        top_sources = {
            item["source"]
            for item in top.get("evidence", [])
        }

        if parser_quality == "LOW" and top_sources & {"protocol", "fallback", "bank_family", "instrument"}:
            conflicts.append("parser_low_quality")

        if top["evidence"][0]["source"] == "fallback":
            conflicts.append("weak_fallback")

        if len(candidates) > 1 and top["score"] - candidates[1]["score"] < 0.08:
            conflicts.append("competing_hypotheses")

        has_rail_transfer = any(
            candidate["category"] == "ELECTRONIC FUND TRANSFER"
            for candidate in candidates
        )
        has_entity_category = entity_category != "UNKNOWN"

        if protocol_rail in RAIL_CATEGORIES and has_rail_transfer and has_entity_category:
            if entity_category != "PAYMENT GATEWAY":
                conflicts.append("rail_entity_ambiguity")
            elif facts["entity"].get("role") in {"payment_processor", "wallet"} and facts["entity"].get("ambiguity") in {"MEDIUM", "HIGH"}:
                conflicts.append("processor_entity_ambiguity")

    return list(dict.fromkeys(conflicts))


def _confidence(top_candidate, facts, conflicts):
    parser_quality = facts["protocol"].get("parse_quality", "LOW")
    top_sources = {
        item["source"]
        for item in top_candidate.get("evidence", [])
    }

    if top_sources & {"protocol", "fallback", "bank_family", "instrument"}:
        quality_multiplier = PARSER_QUALITY_MULTIPLIER.get(parser_quality, 0.82)
    else:
        quality_multiplier = 1.0

    confidence = top_candidate["score"] * quality_multiplier

    for conflict in conflicts:
        confidence -= CONFLICT_PENALTIES.get(conflict, 0.0)

    return round(max(0.0, min(confidence, 1.0)), 2)


def classify_facts(facts):
    evidence = build_evidence(facts)
    candidates = _rank_candidates(evidence)

    if not candidates:
        fallback = FALLBACK_CATEGORY_BY_DIRECTION.get(
            facts["movement"].get("direction", "UNKNOWN"),
            "ELECTRONIC FUND TRANSFER",
        )
        candidates = [
            {
                "category": fallback,
                "score": 0.25,
                "evidence": [
                    _evidence(
                        fallback,
                        "fallback",
                        0.25,
                        "empty_evidence_fallback",
                        "fallback",
                    )
                ],
                "precedence": CATEGORY_PRECEDENCE.get(fallback, 0),
            }
        ]

    conflicts = _detect_conflicts(facts, candidates)
    confidence = _confidence(candidates[0], facts, conflicts)
    review_required = confidence < REVIEW_CONFIDENCE_THRESHOLD or bool(
        set(conflicts)
        & {
            "weak_fallback",
            "competing_hypotheses",
            "deposit_withdrawal_conflict",
            "movement_direction_conflict",
        }
    )

    top = candidates[0]
    alternatives = [
        {
            "category": candidate["category"],
            "score": round(candidate["score"], 3),
        }
        for candidate in candidates[1:4]
    ]

    decision_path = [
        f"{item['source']}:{item['reason']}"
        for item in top["evidence"]
    ]

    evidence_summary = [
        f"{item['category']} <= {item['source']}:{item['reason']} ({item['strength']:.2f})"
        for item in evidence
    ]

    return {
        "category": top["category"],
        "confidence": confidence,
        "matched_rule": top["evidence"][0]["reason"],
        "decision_path": decision_path,
        "conflicts": conflicts,
        "ranked_candidates": [
            {
                "category": candidate["category"],
                "score": round(candidate["score"], 3),
            }
            for candidate in candidates
        ],
        "alternative_categories": alternatives,
        "review_required": review_required,
        "review_reason": " | ".join(conflicts) if conflicts else "",
        "evidence_summary": evidence_summary,
    }
