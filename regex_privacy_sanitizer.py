#!/usr/bin/env python3
"""
regex_privacy_sanitizer.py — Local, deterministic PII detection and sanitization.

Detects sensitive information in free-form text using exhaustive regex patterns
and local heuristics. No network calls, no model downloads, no external dependencies.

Usage:
    python3 regex_privacy_sanitizer.py --text "Contact Jane at jane@example.com"
    python3 regex_privacy_sanitizer.py --text "..." --preserve "1,3"
    python3 regex_privacy_sanitizer.py --text "..." --format json
    python3 regex_privacy_sanitizer.py --list-rules
    echo "Contact Jane at jane@example.com" | python3 regex_privacy_sanitizer.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass

__version__ = "1.0.0"
__all__ = ["detect_private_information", "sanitize_text", "Detection", "PatternSpec"]

# Numeric rank used when resolving overlapping detections.
_CONFIDENCE_RANK: dict[str, int] = {"high": 3, "medium": 2, "low": 1}

_FOLLOW_UP_PROMPT = (
    "Send your own text and I will:\n"
    "  1. detect private information in it,\n"
    "  2. show a numbered annotated view of the original,\n"
    "  3. list all detections with categories and matched spans,\n"
    "  4. let you choose which items to preserve,\n"
    "  5. return the sanitized text with the original for comparison."
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Detection:
    """A single detected PII span within the input text."""

    id: int
    category: str
    placeholder: str
    text: str
    start: int
    end: int
    confidence: str
    rule_id: str
    rule_pattern: str
    rule_flags: str
    rationale: str


@dataclass
class PatternSpec:
    """Definition of a single detection rule, including its rationale."""

    category: str
    placeholder: str
    pattern: str
    confidence: str
    flags: int = re.IGNORECASE
    rationale: str = ""


# ---------------------------------------------------------------------------
# Detection rules
# ---------------------------------------------------------------------------

PATTERNS: list[PatternSpec] = [
    PatternSpec(
        "email address", "[EMAIL]",
        r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b",
        "high",
        rationale="The matched span has the local@domain.tld structure of an email address.",
    ),
    PatternSpec(
        "phone number", "[PHONE]",
        r"(?:(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w))",
        "high",
        rationale="The matched span follows a phone-number digit grouping pattern.",
    ),
    PatternSpec(
        "social handle", "[HANDLE]",
        r"(?<!\w)@[A-Za-z0-9_]{2,32}\b",
        "high",
        flags=0,
        rationale="The matched span starts with @ and fits a social-handle token shape.",
    ),
    PatternSpec(
        "url", "[URL]",
        r"\b(?:https?://|www\.)\S+\b",
        "high",
        rationale="The matched span fits an http(s) or www-style URL pattern.",
    ),
    PatternSpec(
        "ip address", "[IP_ADDRESS]",
        r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b",
        "high",
        flags=0,
        rationale="The matched span fits a dotted-quad IPv4 address pattern.",
    ),
    PatternSpec(
        "mac address", "[MAC_ADDRESS]",
        r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b|\b(?:[0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}\b",
        "high",
        flags=0,
        rationale="The matched span fits a MAC-address hex pair pattern.",
    ),
    PatternSpec(
        "ssn", "[SSN]",
        r"\b\d{3}-\d{2}-\d{4}\b",
        "high",
        flags=0,
        rationale="The matched span fits the common XXX-XX-XXXX SSN pattern.",
    ),
    PatternSpec(
        "ein", "[EIN]",
        r"\b\d{2}-\d{7}\b",
        "medium",
        flags=0,
        rationale="The matched span fits the common XX-XXXXXXX EIN pattern.",
    ),
    PatternSpec(
        "credit card", "[CARD_NUMBER]",
        r"\b(?:\d[ -]*?){13,19}\b",
        "high",
        flags=0,
        rationale="The matched span fits a card-number pattern and also passes a Luhn checksum.",
    ),
    PatternSpec(
        "iban", "[IBAN]",
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
        "high",
        flags=0,
        rationale="The matched span fits the country-code-plus-check-digits shape of an IBAN.",
    ),
    PatternSpec(
        "swift bic", "[SWIFT_BIC]",
        r"\b(?:swift|bic|swift bic|bank code)\s*(?:code|#|no\.?)?\s*[:#-]?\s*[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b",
        "medium",
        rationale="The matched span fits a SWIFT/BIC code pattern near banking keywords.",
    ),
    PatternSpec(
        "routing number", "[ROUTING_NUMBER]",
        r"\b(?:routing|aba)\s*(?:number|#|no\.?)?\s*[:#-]?\s*\d{9}\b",
        "high",
        rationale="The matched span fits a 9-digit routing-number pattern near routing keywords.",
    ),
    PatternSpec(
        "bank account number", "[BANK_ACCOUNT]",
        r"\b(?:account|acct)\s*(?:number|#|no\.?)\s*[:#-]?\s*[A-Z0-9-]{6,20}\b",
        "high",
        rationale="The matched span appears after account-number keywords and fits the account token pattern.",
    ),
    PatternSpec(
        "passport number", "[PASSPORT]",
        r"\bpassport\s*(?:number|#|no\.?)?(?:\s+is)?\s*[:#-]?\s*[A-Z0-9]{6,12}\b",
        "high",
        rationale="The matched span appears after passport keywords and fits the passport token pattern.",
    ),
    PatternSpec(
        "driver license number", "[DRIVER_LICENSE]",
        r"\b(?:driver'?s?|driving|dl)\s*license\s*(?:number|#|no\.?)?\s*[:#-]?\s*[A-Z0-9-]{5,20}\b",
        "high",
        rationale="The matched span appears after license keywords and fits the license token pattern.",
    ),
    PatternSpec(
        "date of birth", "[DOB]",
        r"\b(?:dob|date of birth|born on|birth date)\s*[:#-]?\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|[A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{2,4})\b",
        "high",
        rationale="The matched span appears after DOB-style keywords and fits a date pattern.",
    ),
    PatternSpec(
        "age expression", "[AGE]",
        r"\b(?:age\s*\d{1,3}|\d{1,3}\s*(?:years?\s+old|year-old|year old)|i\s*[\'']?m\s*\d{1,3}|i am\s*\d{1,3}|i am a\s*\d{1,3}\s*year old|i am a\s*\d{1,3}\s*year-old)\b",
        "medium",
        rationale="The matched span explicitly states an age such as 'I'm 23' or '23 years old'.",
    ),
    PatternSpec(
        "relationship or private-life detail", "[RELATIONSHIP_DETAIL]",
        r"\b(?:single|divorced|separated|widowed|break(?:\s+|-)up|broke up|girlfriend|boyfriend|wife|husband|fianc[eé]|fiancee|partner|ex[-\s]?(?:girlfriend|boyfriend|wife|husband|partner))\b",
        "low",
        rationale="The matched span is a relationship-status or private-life keyword.",
    ),
    PatternSpec(
        "single first name in personal context", "[PERSON]",
        r"\b(?:girlfriend|boyfriend|wife|husband|partner|friend|manager|boss|roommate|flatmate|colleague|coworker|co-worker|teacher|doctor)\s+[A-Z][a-z]{2,20}\b",
        "medium",
        flags=0,
        rationale="The matched span pairs a relationship or role word with a capitalized first name.",
    ),
    PatternSpec(
        "single first name", "[PERSON]",
        r"\b(?:named|called|name is)\s+[A-Z][a-z]{2,20}\b",
        "low",
        flags=0,
        rationale="The matched span follows an explicit naming phrase such as 'named Alice'.",
    ),
    PatternSpec(
        "street address", "[ADDRESS]",
        r"\b\d{1,6}\s+(?:[A-Z][a-z0-9.'-]*\s+){0,5}(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl|Terrace|Ter)\b\.?",
        "medium",
        rationale="The matched span starts with a street number and ends with a street-type token.",
    ),
    PatternSpec(
        "standalone street or place mention", "[LOCATION]",
        r"\b(?:[A-Za-z][A-Za-z'-]+\s+(?:Street|St\.?|Road|Rd\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Bd\.?|Lane|Ln\.?|Drive|Dr\.?|Court|Ct\.?|Terrace|Ter\.?)|(?:near|in|around|from|to)\s+(?:the\s+)?[A-Za-z][A-Za-z'-]+\s+(?:Street|St\.?|Road|Rd\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Bd\.?|Lane|Ln\.?|Drive|Dr\.?|Court|Ct\.?|Terrace|Ter\.?))\b",
        "low",
        rationale="The matched span references a named street or place phrase.",
    ),
    PatternSpec(
        "city or place mention", "[LOCATION]",
        r"\b(?:in|near|around|from|to)\s+(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b",
        "low",
        flags=0,
        rationale="The matched span is a preposition followed by one or more capitalized place-like words.",
    ),
    PatternSpec(
        "zip or postal code", "[POSTAL_CODE]",
        r"\b\d{5}(?:-\d{4})?\b|\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b",
        "medium",
        rationale="The matched span fits a US ZIP or UK-style postal-code pattern.",
    ),
    PatternSpec(
        "license plate", "[LICENSE_PLATE]",
        r"\b(?:license plate|plate)\s*[:#-]?\s*[A-Z0-9-]{4,10}\b",
        "medium",
        rationale="The matched span appears after plate keywords and fits the license-plate token pattern.",
    ),
    PatternSpec(
        "medical record number", "[MEDICAL_RECORD_NUMBER]",
        r"\b(?:mrn|medical record|patient id)\s*(?:number|#|no\.?)?\s*[:#-]?\s*[A-Z0-9-]{4,20}\b",
        "high",
        rationale="The matched span appears after medical-record keywords and fits the record token pattern.",
    ),
    PatternSpec(
        "employee or student id", "[INTERNAL_ID]",
        r"\b(?:employee|student|staff|customer|client)\s*(?:id|number|#|no\.?)\s*[:#-]?\s*[A-Z0-9-]{3,20}\b",
        "high",
        rationale="The matched span appears after internal-ID keywords and fits the identifier token pattern.",
    ),
    PatternSpec(
        "account or order id", "[REFERENCE_ID]",
        r"\b(?:account|order|booking|reservation|tracking|invoice|case|ticket)\s*(?:(?:id|number|#|no\.?)\s*[:#-]?\s*[A-Z0-9-]{3,24}|(?:(?=\s+[A-Z0-9-]*\d[A-Z0-9-]{2,23}\b)\s+[A-Z0-9-]{3,24}))\b",
        "medium",
        rationale="The matched span appears after account or order keywords and fits the reference token pattern.",
    ),
    PatternSpec(
        "organization name", "[ORG]",
        r"\b[A-Z][\w&'.-]+(?:\s+[A-Z][\w&'.-]+){0,4}\s+(?:Inc|LLC|Ltd|Corp|Corporation|Company|Co\.|Studio|Agency|University|Hospital|Bank)\b",
        "medium",
        flags=0,
        rationale="The matched span ends with a recognized organization suffix such as Inc, LLC, or University.",
    ),
    PatternSpec(
        "person name with title", "[PERSON]",
        r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b",
        "medium",
        flags=0,
        rationale="The matched span starts with a person title such as Mr, Ms, Dr, or Prof.",
    ),
    PatternSpec(
        "full person name", "[PERSON]",
        r"\b(?!(?:Contact|Call|Email|Text|Meet|Visit|Reach|Message|Thanks|Dear)\b)[A-Z][a-z]{1,20}\s+[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20})?\b",
        "low",
        flags=0,
        rationale="The matched span is a heuristic full-name match of two or more capitalized words.",
    ),
    PatternSpec(
        "bitcoin wallet", "[CRYPTO_WALLET]",
        r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b",
        "medium",
        flags=0,
        rationale="The matched span fits a Bitcoin wallet-address pattern.",
    ),
    PatternSpec(
        "ethereum wallet", "[CRYPTO_WALLET]",
        r"\b0x[a-fA-F0-9]{40}\b",
        "medium",
        flags=0,
        rationale="The matched span fits an Ethereum wallet-address pattern.",
    ),
]


# ---------------------------------------------------------------------------
# Heuristic filter constants
# ---------------------------------------------------------------------------

_PLACE_PAIRS: frozenset[tuple[str, str]] = frozenset({
    ("New", "York"), ("New", "Delhi"), ("Los", "Angeles"),
    ("San", "Francisco"), ("San", "Diego"), ("Las", "Vegas"),
    ("Hong", "Kong"), ("United", "States"), ("New", "Jersey"),
    ("South", "Korea"), ("North", "Carolina"), ("South", "Carolina"),
})

_PLACE_TOKENS: frozenset[str] = frozenset({
    "York", "London", "Paris", "Berlin", "Tokyo", "Boston",
    "Chicago", "Dallas", "Miami", "Seattle", "Austin", "Denver",
    "Toronto", "Sydney", "Dublin", "Delhi",
})

_NON_LOCATION_STARTS: frozenset[str] = frozenset({
    "Contact", "Please", "Review", "Meet", "Call",
    "Email", "Text", "Message", "Ship",
})

_NON_LOCATION_PAIRS: frozenset[tuple[str, str]] = frozenset({
    ("Contact", "Dr"), ("Privacy", "Policy"),
    ("Customer", "Service"), ("Order", "Status"),
})

_COMMON_NON_NAME_TOKENS: frozenset[str] = frozenset({
    "The", "This", "That", "These", "Those", "Please",
    "Privacy", "Policy", "Meet", "Review",
    "Street", "Road", "Avenue", "Beer", "Oxford", "London",
})

_GENERIC_NON_NAME_PAIRS: frozenset[tuple[str, str]] = frozenset({
    ("Privacy", "Policy"), ("Terms", "Conditions"),
    ("Customer", "Service"), ("Order", "Status"),
    ("Account", "Number"),
})


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def normalize_space(text: str) -> str:
    """Collapse runs of whitespace to a single space and strip leading/trailing."""
    return re.sub(r"\s+", " ", text).strip()


def slugify(text: str) -> str:
    """Convert a string to a lowercase hyphen-separated slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def extract_digits(text: str) -> str:
    """Return only the digit characters from *text*."""
    return re.sub(r"\D", "", text)


def build_rule_id(index: int, category: str) -> str:
    return f"rule-{index:02d}-{slugify(category)}"


def flags_to_text(flags: int) -> str:
    """Return a human-readable representation of *re* flag bits."""
    if flags == 0:
        return "NONE"
    parts: list[str] = []
    if flags & re.IGNORECASE:
        parts.append("IGNORECASE")
    if flags & re.MULTILINE:
        parts.append("MULTILINE")
    if flags & re.DOTALL:
        parts.append("DOTALL")
    if flags & re.UNICODE:
        parts.append("UNICODE")
    return "|".join(parts) if parts else str(flags)


def build_rationale(spec: PatternSpec) -> str:
    """Return the full rationale string for *spec*, including a confidence-level note."""
    base = spec.rationale or f'The matched span satisfied the regex rule for "{spec.category}".'
    if spec.confidence == "low":
        return f"{base} This is a heuristic rule — manual review is recommended."
    if spec.confidence == "medium":
        return f"{base} Manual review is advisable as this rule may match broader context."
    return base


# ---------------------------------------------------------------------------
# Validation heuristics
# ---------------------------------------------------------------------------

def passes_luhn(number: str) -> bool:
    """Return True if *number* passes the Luhn checksum (credit card validation)."""
    digits = extract_digits(number)
    if not (13 <= len(digits) <= 19):
        return False
    total = sum(
        (v * 2 - 9 if v * 2 > 9 else v * 2) if i % 2 == 1 else v
        for i, v in enumerate(int(c) for c in reversed(digits))
    )
    return total % 10 == 0


def looks_like_place_name(text: str) -> bool:
    tokens = text.split()
    if len(tokens) < 2:
        return False
    pair = (tokens[0], tokens[1])
    return pair in _PLACE_PAIRS or all(t in _PLACE_TOKENS for t in pair)


def looks_like_non_location_phrase(text: str) -> bool:
    tokens = text.split()
    if not tokens:
        return False
    if len(tokens) >= 2 and (tokens[0], tokens[1]) in _NON_LOCATION_PAIRS:
        return True
    return tokens[0] in _NON_LOCATION_STARTS


def is_plausible_detection(det: Detection) -> bool:
    """Apply post-match heuristic filters to weed out implausible detections."""
    if det.category == "credit card":
        return passes_luhn(det.text)
    if det.category == "full person name":
        tokens = det.text.split()
        pair = (tokens[0], tokens[1]) if len(tokens) >= 2 else ()
        return pair not in _PLACE_PAIRS and pair not in _GENERIC_NON_NAME_PAIRS
    if det.category == "single first name":
        return det.text.strip() not in _COMMON_NON_NAME_TOKENS
    if det.category in {"standalone street or place mention", "city or place mention"}:
        return not looks_like_non_location_phrase(det.text)
    return True


# ---------------------------------------------------------------------------
# Detection pipeline
# ---------------------------------------------------------------------------

def dedupe_detections(detections: list[Detection]) -> list[Detection]:
    """Remove exact-duplicate detections (same span, placeholder, and normalised text)."""
    seen: set[tuple[int, int, str, str]] = set()
    output: list[Detection] = []
    for det in detections:
        key = (det.start, det.end, det.placeholder, det.text.lower())
        if key not in seen:
            seen.add(key)
            output.append(det)
    return output


def resolve_overlaps(detections: list[Detection]) -> list[Detection]:
    """
    Remove overlapping detections, preferring longer spans then higher confidence.
    Reassigns sequential IDs to the surviving set.
    """
    ranked = sorted(
        detections,
        key=lambda d: (d.start, -(d.end - d.start), -_CONFIDENCE_RANK[d.confidence]),
    )
    chosen: list[Detection] = []
    for det in ranked:
        if not any(not (det.end <= kept.start or det.start >= kept.end) for kept in chosen):
            chosen.append(det)
    chosen.sort(key=lambda d: d.start)
    for idx, det in enumerate(chosen, start=1):
        det.id = idx
    return chosen


def detect_private_information(text: str) -> list[Detection]:
    """
    Run all detection rules against *text*.

    Returns a list of deduplicated, non-overlapping detections sorted by
    position in the original text.
    """
    raw: list[Detection] = []
    for rule_index, spec in enumerate(PATTERNS, start=1):
        rule_id = build_rule_id(rule_index, spec.category)
        rule_flags_text = flags_to_text(spec.flags)
        rationale = build_rationale(spec)
        for match in re.finditer(spec.pattern, text, flags=spec.flags):
            matched_text = normalize_space(match.group(0))
            if not matched_text:
                continue
            raw.append(Detection(
                id=0,
                category=spec.category,
                placeholder=spec.placeholder,
                text=matched_text,
                start=match.start(),
                end=match.end(),
                confidence=spec.confidence,
                rule_id=rule_id,
                rule_pattern=spec.pattern,
                rule_flags=rule_flags_text,
                rationale=rationale,
            ))
    filtered = [det for det in raw if is_plausible_detection(det)]
    return resolve_overlaps(dedupe_detections(filtered))


def sanitize_text(
    text: str,
    detections: list[Detection],
    preserve_ids: list[int],
) -> str:
    """
    Replace every detection not in *preserve_ids* with its placeholder string.

    Returns the sanitized text with normalized whitespace.
    """
    preserved = set(preserve_ids)
    to_replace = [det for det in detections if det.id not in preserved]
    if not to_replace:
        return text
    pieces: list[str] = []
    cursor = 0
    for det in to_replace:
        if det.start < cursor:
            continue
        pieces.append(text[cursor:det.start])
        pieces.append(det.placeholder)
        cursor = det.end
    pieces.append(text[cursor:])
    sanitized = "".join(pieces)
    sanitized = re.sub(r"\s+([,.;:!?])", r"\1", sanitized)
    return normalize_space(sanitized)


# ---------------------------------------------------------------------------
# Input parsing / validation
# ---------------------------------------------------------------------------

def parse_preserve_ids(raw: str | None) -> list[int]:
    """Parse a comma-separated string of detection IDs into a sorted list of ints."""
    if not raw or not raw.strip():
        return []
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if not re.fullmatch(r"\d+", part):
            raise ValueError(
                f"Invalid preserve item: {part!r}. Expected comma-separated detection numbers."
            )
        ids.append(int(part))
    return ids


def validate_preserve_ids(preserve_ids: list[int], detections: list[Detection]) -> None:
    """Raise ValueError if any ID in *preserve_ids* is not a valid detection ID."""
    valid = {det.id for det in detections}
    invalid = [v for v in preserve_ids if v not in valid]
    if invalid:
        valid_str = ", ".join(str(v) for v in sorted(valid)) or "(none)"
        raise ValueError(
            f"Invalid preserve ID(s): {', '.join(str(v) for v in invalid)}. "
            f"Valid detection numbers: {valid_str}."
        )


# ---------------------------------------------------------------------------
# Rendering — text format
# ---------------------------------------------------------------------------

def render_annotated_text(text: str, detections: list[Detection]) -> str:
    """Return *text* with each detected span wrapped in <<id:span>> markers."""
    if not detections:
        return text
    pieces: list[str] = []
    cursor = 0
    for det in detections:
        if det.start < cursor:
            continue
        pieces.append(text[cursor:det.start])
        pieces.append(f"<<{det.id}:{text[det.start:det.end]}>>")
        cursor = det.end
    pieces.append(text[cursor:])
    return "".join(pieces)


def render_summary_list(detections: list[Detection]) -> str:
    lines = ["Summary:"]
    for det in detections:
        lines.append(
            f'{det.id}. "{det.text}" → {det.category} | {det.placeholder} | confidence: {det.confidence}'
        )
    return "\n".join(lines)


def render_context_snippet(text: str, start: int, end: int, radius: int = 28) -> str:
    """Return the matched span with up to *radius* characters of surrounding context."""
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    prefix = ("..." if left > 0 else "") + text[left:start]
    suffix = text[end:right] + ("..." if right < len(text) else "")
    return f"{prefix}[{text[start:end]}]{suffix}"


def render_reviewer_audit(detections: list[Detection]) -> str:
    counts = Counter(det.confidence for det in detections)
    lines = [
        "Reviewer audit notes:",
        "engine=local-deterministic-regex | hosted_model_calls=no | local_model_downloads=no | network_required=no",
        (
            f"pattern_count={len(PATTERNS)} | detections={len(detections)} | "
            f"high={counts.get('high', 0)} | medium={counts.get('medium', 0)} | low={counts.get('low', 0)}"
        ),
        "verification_surfaces=annotated text, matched text, span offsets, local context, "
        "confidence, placeholder, rule id, regex pattern, regex flags",
    ]
    if counts.get("low", 0):
        lines.append(
            "manual_review_recommended=yes (one or more low-confidence heuristic detections)"
        )
    return "\n".join(lines)


def render_detailed_list(text: str, detections: list[Detection]) -> str:
    lines = ["Detailed detections (reviewer format):"]
    for det in detections:
        lines.extend([
            f"{det.id}. category={det.category} | placeholder={det.placeholder} | "
            f"confidence={det.confidence} | span=[{det.start},{det.end}) | rule_id={det.rule_id}",
            f'   matched_text="{det.text}"',
            f'   context="{render_context_snippet(text, det.start, det.end)}"',
            f"   rationale={det.rationale}",
            f"   regex={det.rule_pattern}",
            f"   flags={det.rule_flags}",
        ])
    return "\n".join(lines)


def render_comparison(original: str, sanitized: str, *, preview: bool) -> str:
    after_label = "After (sanitized preview):" if preview else "After (sanitized text):"
    return f"Before:\n{original}\n\n{after_label}\n{sanitized}"


def render_next_step(detections: list[Detection], preserve_requested: bool) -> str:
    if not detections:
        return "Next step:\nNo preserve step needed — nothing was detected."
    if preserve_requested:
        return (
            "Next step:\n"
            "To change the preserve selection, reply with the detection number(s) to keep."
        )
    return (
        "Next step:\n"
        "Reply with any number(s) you want to preserve. "
        "If none, all detected items will be replaced."
    )


def render_text_report(
    text: str,
    detections: list[Detection],
    preserve_ids: list[int],
    sanitized: str,
    preserve_requested: bool,
) -> str:
    """Assemble the full human-readable output report."""
    if not detections:
        return "\n\n".join([
            "No private information detected with the current rule set.",
            render_reviewer_audit(detections),
            f"Original text:\n{text}",
            f"Sanitized text:\n{sanitized}",
            render_comparison(text, sanitized, preview=False),
            f"Try another text:\n{_FOLLOW_UP_PROMPT}",
        ])

    n = len(detections)
    if preserve_requested and preserve_ids:
        preserve_label = ", ".join(str(v) for v in preserve_ids)
        sanitized_section = f"Sanitized text (preserving item(s) {preserve_label}):\n{sanitized}"
    elif preserve_requested:
        sanitized_section = f"Sanitized text:\n{sanitized}"
    else:
        sanitized_section = f"Sanitized preview ({n} item(s) replaced):\n{sanitized}"

    return "\n\n".join([
        f"I detected {n} item(s) of private information in your text:",
        render_reviewer_audit(detections),
        f"Original text:\n{text}",
        f"Annotated input ({n} detection(s) marked):\n{render_annotated_text(text, detections)}",
        render_summary_list(detections),
        render_detailed_list(text, detections),
        sanitized_section,
        render_comparison(text, sanitized, preview=not preserve_requested),
        render_next_step(detections, preserve_requested),
        f"Try another text:\n{_FOLLOW_UP_PROMPT}",
    ])


# ---------------------------------------------------------------------------
# Rendering — JSON format
# ---------------------------------------------------------------------------

def build_engine_metadata() -> dict:
    return {
        "engine_name": "regex-privacy-sanitizer",
        "version": __version__,
        "deterministic": True,
        "uses_hosted_model": False,
        "uses_local_model": False,
        "network_required": False,
        "pattern_count": len(PATTERNS),
        "heuristic_filters": [
            "Luhn validation for credit-card candidates",
            "place-name suppression for full-name heuristics",
            "non-location phrase suppression for location heuristics",
            "common-token suppression for single-name heuristics",
        ],
        "reviewer_fields": [
            "matched_text", "start", "end", "context",
            "confidence", "placeholder", "rule_id",
            "rule_pattern", "rule_flags", "rationale",
        ],
    }


def build_rule_catalog() -> list[dict]:
    return [
        {
            "rule_id": build_rule_id(i, spec.category),
            "category": spec.category,
            "placeholder": spec.placeholder,
            "confidence": spec.confidence,
            "regex": spec.pattern,
            "flags": flags_to_text(spec.flags),
            "rationale": build_rationale(spec),
        }
        for i, spec in enumerate(PATTERNS, start=1)
    ]


# ---------------------------------------------------------------------------
# Rule catalog rendering — text format
# ---------------------------------------------------------------------------

def render_rule_catalog_text() -> str:
    lines = [
        "Rule catalog:",
        f"{len(PATTERNS)} rules — all local and deterministic, no model required.",
        "",
    ]
    for rule in build_rule_catalog():
        lines.extend([
            f"  rule_id={rule['rule_id']} | category={rule['category']} | "
            f"placeholder={rule['placeholder']} | confidence={rule['confidence']} | flags={rule['flags']}",
            f"    rationale={rule['rationale']}",
            f"    regex={rule['regex']}",
            "",
        ])
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="regex_privacy_sanitizer",
        description=(
            "Local, deterministic PII detection and sanitization. "
            "No network calls, no model downloads."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s --text \"Contact Jane at jane@example.com\"\n"
            "  %(prog)s --text \"...\" --preserve \"1,3\"\n"
            "  %(prog)s --text \"...\" --format json\n"
            "  %(prog)s --list-rules\n"
            "  echo \"Jane Doe, jane@example.com\" | %(prog)s\n"
        ),
    )
    parser.add_argument(
        "--text",
        metavar="TEXT",
        help="Input text to analyze. Omit to read from stdin.",
    )
    parser.add_argument(
        "--preserve",
        metavar="IDS",
        default=None,
        help="Comma-separated detection numbers to keep in the sanitized output (e.g. '1,3').",
    )
    parser.add_argument(
        "--list-rules",
        action="store_true",
        help="Print the full detection rule catalog and exit.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.list_rules:
        if args.format == "json":
            print(json.dumps(
                {"engine": build_engine_metadata(), "rules": build_rule_catalog()},
                indent=2,
                ensure_ascii=False,
            ))
        else:
            print(render_rule_catalog_text())
        return

    # Resolve input: --text flag takes priority, then stdin.
    if args.text:
        input_text = args.text
    elif not sys.stdin.isatty():
        input_text = sys.stdin.read().strip()
    else:
        parser.error("Provide input via --text TEXT or pipe text via stdin.")
        return  # unreachable; silences type checkers

    if not input_text:
        parser.error("Input text is empty.")

    detections = detect_private_information(input_text)

    try:
        preserve_ids = parse_preserve_ids(args.preserve)
        validate_preserve_ids(preserve_ids, detections)
    except ValueError as exc:
        parser.error(str(exc))
        return

    preserve_requested = args.preserve is not None
    sanitized = sanitize_text(input_text, detections, preserve_ids)

    if args.format == "json":
        payload = {
            "engine": build_engine_metadata(),
            "original_text": input_text,
            "annotated_text": render_annotated_text(input_text, detections),
            "detections": [
                {
                    **asdict(det),
                    "context": render_context_snippet(input_text, det.start, det.end),
                }
                for det in detections
            ],
            "preserve_ids": preserve_ids,
            "preserve_requested": preserve_requested,
            "sanitized_text": sanitized,
            "next_step": render_next_step(detections, preserve_requested),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    print(render_text_report(input_text, detections, preserve_ids, sanitized, preserve_requested))


if __name__ == "__main__":
    main()
