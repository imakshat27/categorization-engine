import re


TOKEN_CHARS = "A-Z0-9"


def _normalize_for_match(text):
    if text is None:
        return ""

    return str(text).upper()


def token_pattern(term):
    term = _normalize_for_match(term).strip()

    if not term:
        return r"$^"

    pieces = [
        re.escape(piece)
        for piece in re.split(r"[\s/_\-.:\[\](),@]+", term)
        if piece
    ]
    phrase = r"[\s/_\-.:\[\](),@]*".join(pieces)

    return rf"(?<![{TOKEN_CHARS}]){phrase}(?![{TOKEN_CHARS}])"


def regex_match(pattern, text, rule_name=None, source=None, flags=0):
    normalized = _normalize_for_match(text)
    match = re.search(pattern, normalized, flags | re.IGNORECASE)

    if not match:
        return None

    return {
        "rule_name": rule_name or pattern,
        "pattern": pattern,
        "source": source or "regex",
        "match": match.group(0),
        "span": match.span(),
        "groups": match.groups(),
    }


def token_match(term, text, rule_name=None, source=None):
    return regex_match(
        token_pattern(term),
        text,
        rule_name=rule_name or term,
        source=source or "token",
    )


def first_token_match(terms, text, rule_name=None, source=None):
    for term in terms:
        match = token_match(
            term,
            text,
            rule_name=rule_name or term,
            source=source,
        )

        if match:
            match["term"] = term
            return match

    return None


def any_token_match(terms, text, rule_name=None, source=None):
    matches = []

    for term in terms:
        match = token_match(
            term,
            text,
            rule_name=rule_name or term,
            source=source,
        )

        if match:
            match["term"] = term
            matches.append(match)

    return matches


def compact_tokens(text):
    normalized = _normalize_for_match(text)
    return re.findall(r"[A-Z0-9]+", normalized)


def clean_entity_text(text):
    normalized = _normalize_for_match(text)
    normalized = re.sub(r"\(VALUE DATE:?[^)]*\)", " ", normalized)
    normalized = re.sub(r"\bVALUE\s*DATE\b.*", " ", normalized)
    normalized = re.sub(r"\bNA\b", " ", normalized)
    normalized = re.sub(r"\bUPI\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip(" /-:_")
