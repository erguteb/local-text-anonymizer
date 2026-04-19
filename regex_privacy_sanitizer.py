#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from typing import List, Sequence


@dataclass
class Detection:
    id: int
    category: str
    placeholder: str
    text: str
    start: int
    end: int
    confidence: str


@dataclass
class PatternSpec:
    category: str
    placeholder: str
    pattern: str
    confidence: str
    flags: int = re.IGNORECASE


PATTERNS: List[PatternSpec] = [
    PatternSpec("email address", "[EMAIL]", r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", "high"),
    PatternSpec(
        "phone number",
        "[PHONE]",
        r"(?:(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w))",
        "high",
    ),
    PatternSpec("social handle", "[HANDLE]", r"(?<!\w)@[A-Za-z0-9_]{2,32}\b", "high", flags=0),
    PatternSpec("url", "[URL]", r"\b(?:https?://|www\.)\S+\b", "high"),
    PatternSpec(
        "ip address",
        "[IP_ADDRESS]",
        r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b",
        "high",
        flags=0,
    ),
    PatternSpec(
        "mac address",
        "[MAC_ADDRESS]",
        r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b|\b(?:[0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}\b",
        "high",
        flags=0,
    ),
    PatternSpec("ssn", "[SSN]", r"\b\d{3}-\d{2}-\d{4}\b", "high", flags=0),
    PatternSpec("ein", "[EIN]", r"\b\d{2}-\d{7}\b", "medium", flags=0),
    PatternSpec(
        "credit card",
        "[CARD_NUMBER]",
        r"\b(?:\d[ -]*?){13,19}\b",
        "high",
        flags=0,
    ),
    PatternSpec(
        "iban",
        "[IBAN]",
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
        "high",
        flags=0,
    ),
    PatternSpec(
        "swift bic",
        "[SWIFT_BIC]",
        r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b",
        "medium",
        flags=0,
    ),
    PatternSpec(
        "routing number",
        "[ROUTING_NUMBER]",
        r"\b(?:routing|aba)\s*(?:number|#|no\.?)?\s*[:#-]?\s*\d{9}\b",
        "high",
    ),
    PatternSpec(
        "bank account number",
        "[BANK_ACCOUNT]",
        r"\b(?:account|acct)\s*(?:number|#|no\.?)\s*[:#-]?\s*[A-Z0-9-]{6,20}\b",
        "high",
    ),
    PatternSpec(
        "passport number",
        "[PASSPORT]",
        r"\bpassport\s*(?:number|#|no\.?)?(?:\s+is)?\s*[:#-]?\s*[A-Z0-9]{6,12}\b",
        "high",
    ),
    PatternSpec(
        "driver license number",
        "[DRIVER_LICENSE]",
        r"\b(?:driver'?s?|driving|dl)\s*license\s*(?:number|#|no\.?)?\s*[:#-]?\s*[A-Z0-9-]{5,20}\b",
        "high",
    ),
    PatternSpec(
        "date of birth",
        "[DOB]",
        r"\b(?:dob|date of birth|born on|birth date)\s*[:#-]?\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|[A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{2,4})\b",
        "high",
    ),
    PatternSpec(
        "age expression",
        "[AGE]",
        r"\b(?:age\s*\d{1,3}|\d{1,3}\s*(?:years old|year-old)|i\s*[\'’]?m\s*\d{1,3}|i am\s*\d{1,3})\b",
        "medium",
    ),
    PatternSpec(
        "street address",
        "[ADDRESS]",
        r"\b\d{1,6}\s+(?:[A-Z][a-z0-9.'-]*\s+){0,5}(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl|Terrace|Ter)\b\.?",
        "medium",
    ),
    PatternSpec(
        "zip or postal code",
        "[POSTAL_CODE]",
        r"\b\d{5}(?:-\d{4})?\b|\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b",
        "medium",
    ),
    PatternSpec(
        "license plate",
        "[LICENSE_PLATE]",
        r"\b(?:license plate|plate)\s*[:#-]?\s*[A-Z0-9-]{4,10}\b",
        "medium",
    ),
    PatternSpec(
        "medical record number",
        "[MEDICAL_RECORD_NUMBER]",
        r"\b(?:mrn|medical record|patient id)\s*(?:number|#|no\.?)?\s*[:#-]?\s*[A-Z0-9-]{4,20}\b",
        "high",
    ),
    PatternSpec(
        "employee or student id",
        "[INTERNAL_ID]",
        r"\b(?:employee|student|staff|customer|client)\s*(?:id|number|#|no\.?)\s*[:#-]?\s*[A-Z0-9-]{3,20}\b",
        "high",
    ),
    PatternSpec(
        "account or order id",
        "[REFERENCE_ID]",
        r"\b(?:account|order|booking|reservation|tracking|invoice|case|ticket)\s*(?:(?:id|number|#|no\.?)\s*[:#-]?\s*|\s+)(?=[A-Z0-9-]{3,24}\b)(?:[A-Z]*\d[A-Z0-9-]*|\d[A-Z0-9-]{2,23})\b",
        "medium",
    ),
    PatternSpec(
        "organization name",
        "[ORG]",
        r"\b[A-Z][\w&'.-]+(?:\s+[A-Z][\w&'.-]+){0,4}\s+(?:Inc|LLC|Ltd|Corp|Corporation|Company|Co\.|Studio|Agency|University|Hospital|Bank)\b",
        "medium",
        flags=0,
    ),
    PatternSpec(
        "person name with title",
        "[PERSON]",
        r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b",
        "medium",
        flags=0,
    ),
    PatternSpec(
        "full person name",
        "[PERSON]",
        r"\b(?!(?:Contact|Call|Email|Text|Meet|Visit|Reach|Message|Thanks|Dear)\b)[A-Z][a-z]{1,20}\s+[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20})?\b",
        "low",
        flags=0,
    ),
    PatternSpec(
        "bitcoin wallet",
        "[CRYPTO_WALLET]",
        r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b",
        "medium",
        flags=0,
    ),
    PatternSpec(
        "ethereum wallet",
        "[CRYPTO_WALLET]",
        r"\b0x[a-fA-F0-9]{40}\b",
        "medium",
        flags=0,
    ),
]


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def dedupe_detections(detections: Sequence[Detection]) -> List[Detection]:
    seen = set()
    output: List[Detection] = []
    for det in detections:
        key = (det.start, det.end, det.placeholder, det.text.lower())
        if key in seen:
            continue
        seen.add(key)
        output.append(det)
    return output


def resolve_overlaps(detections: Sequence[Detection]) -> List[Detection]:
    ranked = sorted(
        detections,
        key=lambda d: (d.start, -(d.end - d.start), -{"high": 3, "medium": 2, "low": 1}[d.confidence]),
    )
    chosen: List[Detection] = []
    for det in ranked:
        overlap = False
        for kept in chosen:
            if not (det.end <= kept.start or det.start >= kept.end):
                overlap = True
                break
        if not overlap:
            chosen.append(det)
    chosen.sort(key=lambda d: d.start)
    for idx, det in enumerate(chosen, start=1):
        det.id = idx
    return chosen


def detect_private_information(text: str) -> List[Detection]:
    raw: List[Detection] = []
    for spec in PATTERNS:
        for match in re.finditer(spec.pattern, text, flags=spec.flags):
            matched_text = normalize_space(match.group(0))
            if not matched_text:
                continue
            raw.append(
                Detection(
                    id=0,
                    category=spec.category,
                    placeholder=spec.placeholder,
                    text=matched_text,
                    start=match.start(),
                    end=match.end(),
                    confidence=spec.confidence,
                )
            )
    return resolve_overlaps(dedupe_detections(raw))


def sanitize_text(text: str, detections: Sequence[Detection], preserve_ids: Sequence[int]) -> str:
    preserve = set(preserve_ids)
    kept = [det for det in detections if det.id not in preserve]
    if not kept:
        return text
    pieces: List[str] = []
    cursor = 0
    for det in kept:
        if det.start < cursor:
            continue
        pieces.append(text[cursor:det.start])
        pieces.append(det.placeholder)
        cursor = det.end
    pieces.append(text[cursor:])
    sanitized = "".join(pieces)
    sanitized = re.sub(r"\s+([,.;:!?])", r"\1", sanitized)
    return normalize_space(sanitized)


def parse_preserve_ids(raw: str) -> List[int]:
    if not raw.strip():
        return []
    ids: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if not re.fullmatch(r"\d+", part):
            raise argparse.ArgumentTypeError(
                f"invalid preserve list item: {part!r}. Expected comma-separated detection numbers."
            )
        ids.append(int(part))
    return ids


def render_detection_list(detections: Sequence[Detection]) -> str:
    if not detections:
        return "In your text, I detected no obvious private information with the current regex rules."
    lines = ["In your text, I detected certain private information, here is all of them:"]
    for det in detections:
        lines.append(
            f"{det.id}. {det.category} -> {det.placeholder} | confidence={det.confidence} | match={det.text}"
        )
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Regex-only privacy sanitizer with detection review and preserve-by-number support."
    )
    parser.add_argument("--text", required=True, help="Input text to analyze and sanitize.")
    parser.add_argument(
        "--preserve",
        default="",
        help="Comma-separated detection numbers to preserve in the final sanitized text.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    detections = detect_private_information(args.text)
    try:
        preserve_ids = parse_preserve_ids(args.preserve)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    should_render_sanitized = bool(preserve_ids) or not detections
    sanitized = sanitize_text(args.text, detections, preserve_ids) if should_render_sanitized else None

    if args.format == "json":
        payload = {
            "message": render_detection_list(detections),
            "detections": [asdict(det) for det in detections],
            "preserve_ids": preserve_ids,
            "sanitized_text": sanitized,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return

    print(render_detection_list(detections))
    if detections:
        print("\nIf you want to preserve any detected item, reply with its number(s).")
    if should_render_sanitized:
        print("\nSanitized text:")
        print(sanitized)


if __name__ == "__main__":
    main()
