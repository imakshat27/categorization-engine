from engine.classifier import classify_transaction
from engine.normalizer import normalize_text
from engine.semantic import build_semantic_facts, detect_direction


def _protocol(facts, key, default="UNKNOWN"):
    return facts.get("protocol", {}).get(key, default)


def _entity(facts, key, default="UNKNOWN"):
    return facts.get("entity", {}).get(key, default)


def _movement(facts, key, default="UNKNOWN"):
    return facts.get("movement", {}).get(key, default)


def _intent_tags(facts):
    return set(facts.get("intent", {}).get("tags", []))


def _movement_tags(facts):
    return set(facts.get("movement", {}).get("tags", []))


def _join(items):
    return " | ".join(str(item) for item in items if item not in (None, ""))


def _format_candidates(candidates):
    return _join(
        f"{candidate['category']}:{candidate['score']}"
        for candidate in candidates
    )


def process_transactions(df):
    df["Normalized Narration"] = df["Narration"].apply(normalize_text)

    df["Direction"] = df.apply(detect_direction, axis=1)

    semantic_results = df.apply(build_semantic_facts, axis=1)
    df["Semantic Facts"] = semantic_results

    df["Mode"] = semantic_results.apply(lambda facts: _protocol(facts, "rail"))
    df["Protocol Family"] = semantic_results.apply(lambda facts: _protocol(facts, "family"))
    df["Parser Rule"] = semantic_results.apply(lambda facts: _protocol(facts, "parser_rule"))
    df["Parser Confidence"] = semantic_results.apply(lambda facts: _protocol(facts, "parser_confidence", 0.0))

    df["Transaction Prefix"] = semantic_results.apply(lambda facts: _protocol(facts, "transaction_prefix"))
    df["Transaction Subtype"] = semantic_results.apply(lambda facts: _protocol(facts, "subtype"))
    df["Reference ID"] = semantic_results.apply(lambda facts: _protocol(facts, "reference_id"))
    df["Entity Name"] = semantic_results.apply(lambda facts: _protocol(facts, "counterparty"))
    df["Bank Name"] = semantic_results.apply(lambda facts: _protocol(facts, "bank"))
    df["UPI ID"] = semantic_results.apply(lambda facts: _protocol(facts, "upi_id"))
    df["UPI Handle"] = semantic_results.apply(lambda facts: _protocol(facts, "handle"))
    df["Parse Quality"] = semantic_results.apply(lambda facts: _protocol(facts, "parse_quality"))

    df["Merchant"] = semantic_results.apply(lambda facts: _entity(facts, "canonical"))
    df["Entity Type"] = semantic_results.apply(lambda facts: _entity(facts, "category"))
    df["Entity Role"] = semantic_results.apply(lambda facts: _entity(facts, "role"))
    df["Entity Confidence"] = semantic_results.apply(lambda facts: _entity(facts, "confidence", 0.0))
    df["Matched Entity Rule"] = semantic_results.apply(lambda facts: _entity(facts, "matched_alias"))

    df["Instrument Type"] = semantic_results.apply(lambda facts: _movement(facts, "instrument_type"))
    df["Intent Tags"] = semantic_results.apply(lambda facts: _join(facts.get("intent", {}).get("tags", [])))
    df["Movement Tags"] = semantic_results.apply(lambda facts: _join(facts.get("movement", {}).get("tags", [])))
    df["Bank Family"] = semantic_results.apply(lambda facts: facts.get("bank_family", {}).get("family", "UNKNOWN"))

    df["Bounce Flag"] = semantic_results.apply(lambda facts: "bounce" in _intent_tags(facts))
    df["Charge Flag"] = semantic_results.apply(lambda facts: "charge" in _intent_tags(facts))
    df["Reversal Flag"] = semantic_results.apply(lambda facts: "reversal" in _intent_tags(facts))
    df["Salary Flag"] = semantic_results.apply(lambda facts: "salary" in _intent_tags(facts))
    df["Tax Flag"] = semantic_results.apply(lambda facts: "tax" in _intent_tags(facts))
    df["Cash Flag"] = semantic_results.apply(lambda facts: "cash" in _movement_tags(facts))
    df["Deposit Flag"] = semantic_results.apply(lambda facts: "deposit" in _movement_tags(facts))
    df["Withdrawal Flag"] = semantic_results.apply(lambda facts: "withdrawal" in _movement_tags(facts))
    df["ATM Flag"] = semantic_results.apply(lambda facts: "atm" in _movement_tags(facts))
    df["Cheque Flag"] = semantic_results.apply(lambda facts: "cheque" in _movement_tags(facts))
    df["Investment Flag"] = semantic_results.apply(lambda facts: "investment" in _intent_tags(facts))
    df["Insurance Flag"] = semantic_results.apply(lambda facts: "insurance" in _intent_tags(facts))
    df["Recharge Flag"] = semantic_results.apply(lambda facts: "recharge" in _intent_tags(facts))
    df["Travel Flag"] = semantic_results.apply(lambda facts: "travel" in _intent_tags(facts))
    df["Utility Flag"] = semantic_results.apply(lambda facts: "utility" in _intent_tags(facts))
    df["Loan Flag"] = semantic_results.apply(lambda facts: "loan" in _intent_tags(facts))

    classification_results = df.apply(classify_transaction, axis=1)

    df["Category"] = classification_results.apply(lambda result: result["category"])
    df["Confidence"] = classification_results.apply(lambda result: result["confidence"])
    df["Decision Path"] = classification_results.apply(lambda result: _join(result.get("decision_path", [])))
    df["Conflicts"] = classification_results.apply(lambda result: _join(result.get("conflicts", [])))
    df["Matched Rule"] = classification_results.apply(lambda result: result["matched_rule"])
    df["Ranked Candidates"] = classification_results.apply(lambda result: _format_candidates(result.get("ranked_candidates", [])))
    df["Alternative Categories"] = classification_results.apply(lambda result: _format_candidates(result.get("alternative_categories", [])))
    df["Review Required"] = classification_results.apply(lambda result: result.get("review_required", False))
    df["Review Reason"] = classification_results.apply(lambda result: result.get("review_reason", ""))
    df["Evidence Summary"] = classification_results.apply(lambda result: _join(result.get("evidence_summary", [])))

    return df

