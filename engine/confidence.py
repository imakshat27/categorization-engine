def build_classification(

    category,

    matched_rule,

    base_confidence,

    decision_path,

    conflicts=None
):

    # default empty conflicts
    if conflicts is None:
        conflicts = []


    confidence = base_confidence


    # =====================================
    # CONFLICT PENALTIES
    # =====================================

    conflict_penalties = {

        "deposit_withdrawal_conflict": 0.20,

        "cash_cheque_conflict": 0.15,

        "weak_signal_match": 0.25
    }


    for conflict in conflicts:

        if conflict in conflict_penalties:

            confidence -= conflict_penalties[
                conflict
            ]


    # =====================================
    # CLAMP CONFIDENCE
    # =====================================

    confidence = max(
        0.0,
        min(confidence, 1.0)
    )


    # round nicely
    confidence = round(confidence, 2)


    return {

        "category": category,

        "confidence": confidence,

        "decision_path": decision_path,

        "conflicts": conflicts,

        "matched_rule": matched_rule
    }