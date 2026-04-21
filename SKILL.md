---
name: local-text-anonymizer
description: Use when the user wants deterministic, offline text sanitization with no LLM or model dependency. Detects PII using exhaustive regex and rule-based patterns, presents a numbered review list, lets the user preserve selected items, and returns sanitized text with placeholders such as [EMAIL] or [PHONE].
---

# Local Text Anonymizer

A fully deterministic, offline privacy-sanitization skill. Detection and replacement use regex and local heuristics only — no hosted LLM, local model, embedding, or classifier is involved at any point.

---

## Installation

This skill is a **folder-based artifact**. Both files must be present in the same directory:

```text
local-text-anonymizer/
├── SKILL.md
└── regex_privacy_sanitizer.py
```

`SKILL.md` alone is an incomplete installation. If only `SKILL.md` is present, fetch the full repository before proceeding:

```bash
git clone https://github.com/erguteb/local-text-anonymizer
cd local-text-anonymizer
python3 regex_privacy_sanitizer.py --text "Contact Jane Doe at jane@example.com."
```

The skill has no runtime dependencies beyond the Python standard library — no package installs, no network calls, no model downloads.

**Source repository:** `https://github.com/erguteb/local-text-anonymizer`

---

## When to Use This Skill

Use when the user wants:

- PII removed from text before sharing it elsewhere
- Placeholders such as `[EMAIL]`, `[PHONE]`, `[PERSON]`, `[ADDRESS]`
- An interactive review step before replacement
- Preserve-by-number control over which detections to keep
- A fully offline, deterministic tool with no model dependencies

Do **not** use when the user wants semantic paraphrasing, contextual rewriting, or model-based anonymization.

---

## Detection Categories

The bundled script detects 33 categories using exhaustive regex and local heuristics:

| Category | Placeholder |
|---|---|
| Email addresses | `[EMAIL]` |
| Phone numbers | `[PHONE]` |
| Social media handles | `[SOCIAL_HANDLE]` |
| URLs | `[URL]` |
| IP addresses | `[IP_ADDRESS]` |
| MAC addresses | `[MAC_ADDRESS]` |
| SSNs | `[SSN]` |
| EINs | `[EIN]` |
| Credit card numbers | `[CREDIT_CARD]` |
| IBANs | `[IBAN]` |
| SWIFT/BIC codes | `[SWIFT_BIC]` |
| Routing numbers | `[ROUTING_NUMBER]` |
| Bank account numbers | `[BANK_ACCOUNT]` |
| Passport numbers | `[PASSPORT]` |
| Driver license numbers | `[DRIVER_LICENSE]` |
| Date-of-birth expressions | `[DATE_OF_BIRTH]` |
| Age expressions | `[AGE]` |
| Street addresses | `[ADDRESS]` |
| Zip/postal codes | `[POSTAL_CODE]` |
| License plates | `[LICENSE_PLATE]` |
| Medical record numbers | `[MEDICAL_RECORD]` |
| Employee/student/customer IDs | `[ID]` |
| Account/order/tracking reference IDs | `[REFERENCE_ID]` |
| Organization names | `[ORGANIZATION]` |
| Person names with titles | `[PERSON]` |
| Heuristic full names | `[PERSON]` |
| Bitcoin wallets | `[BITCOIN_WALLET]` |
| Ethereum wallets | `[ETH_WALLET]` |

Detection scope is intentionally broad. High-confidence categories match exact formats (e.g., email, credit card). Medium- and low-confidence categories use heuristics (e.g., names, organizations) and may produce false positives. Always preserve the script's confidence labels when presenting results to the user.

---

## CLI Reference

**Basic detection and sanitization:**
```bash
python3 regex_privacy_sanitizer.py --text "I'm 23, email me at jane@example.com or call (415) 555-1212."
```

**Preserve selected items by number:**
```bash
python3 regex_privacy_sanitizer.py \
  --text "I'm 23, email me at jane@example.com or call (415) 555-1212." \
  --preserve "1,3"
```

**Read from stdin (pipe-friendly):**
```bash
echo "Contact Jane Doe at jane@example.com." | python3 regex_privacy_sanitizer.py
cat document.txt | python3 regex_privacy_sanitizer.py --format json
```

**Structured JSON output:**
```bash
python3 regex_privacy_sanitizer.py \
  --text "Contact Jane Doe at jane@example.com." \
  --format json
```

**Inspect the full rule catalog:**
```bash
python3 regex_privacy_sanitizer.py --list-rules
python3 regex_privacy_sanitizer.py --list-rules --format json
```

**Print version:**
```bash
python3 regex_privacy_sanitizer.py --version
```

---

## Interaction Protocol

When the user provides text to sanitize, follow this two-step flow:

### Step 1 — Detect

Run the script without `--preserve`:

```bash
python3 regex_privacy_sanitizer.py --text "<user text>"
```

Present the results in this format:

```
In your text, I detected the following private information:

Original text:
<original>

Annotated input:
<<1:matched span>>, rest of text <<2:another span>>.

Summary:
1. "<matched text>" → <category> | [PLACEHOLDER] | confidence: <level>
2. ...

Detailed detections:
1. category=<category> | placeholder=[X] | confidence=<level> | matched_text="..."
2. ...

Before: <original text>
After:  <sanitized preview>

Reply with any number(s) you want to preserve. If none, all detected items will be replaced.
```

### Step 2 — Sanitize

If the user specifies items to preserve, pass them via `--preserve`:

```bash
python3 regex_privacy_sanitizer.py --text "<user text>" --preserve "2,5"
```

Return:
1. The final sanitized text
2. The original text for comparison
3. A prompt inviting the user to try another input

If no items are flagged for preservation, sanitize all detections and return the same output.

If nothing is detected, say so directly and return the original text unchanged.

---

## Demo Workflow

When the user requests a demo (`test the skill`, `show how it works`, `try the skill`, etc.), run the built-in demo text through the full two-step flow before asking for the user's own input.

**Demo input:**
```
I am a 23 year old guy single in London. I just broke up with my girlfriend Lily. Do you know any good place for beer near Oxford Street?
```

For this demo, do not summarize loosely. Show the input, the detected private information as a numbered list, and the anonymized output explicitly.

Use an artifact-style presentation like this:

```text
Demo input:
I am a 23 year old guy single in London. I just broke up with my girlfriend Lily. Do you know any good place for beer near Oxford Street?

Detected private information:
1. age expression -> [AGE] | confidence=medium | match=I am a 23 year old
2. relationship or private-life detail -> [RELATIONSHIP_DETAIL] | confidence=low | match=single
3. city or place mention -> [LOCATION] | confidence=low | match=in London
4. relationship or private-life detail -> [RELATIONSHIP_DETAIL] | confidence=low | match=broke up
5. single first name in personal context -> [PERSON] | confidence=medium | match=girlfriend Lily
6. standalone street or place mention -> [LOCATION] | confidence=low | match=near Oxford Street

Anonymized output with all detections replaced:
[AGE] guy [RELATIONSHIP_DETAIL] [LOCATION]. I just [RELATIONSHIP_DETAIL] with my [PERSON]. Do you know any good place for beer [LOCATION]?
```

Then ask which items to preserve. For this demo, item 6 (the street location) is a good candidate to preserve, as it keeps useful context for a downstream query while masking the more sensitive personal details.

Run the second pass with `--preserve "6"` and show the result alongside the original.

Show the second pass explicitly too:

```text
Demo input:
I am a 23 year old guy single in London. I just broke up with my girlfriend Lily. Do you know any good place for beer near Oxford Street?

Preserved item(s):
6

Anonymized output with preserve choice applied:
[AGE] guy [RELATIONSHIP_DETAIL] [LOCATION]. I just [RELATIONSHIP_DETAIL] with my [PERSON]. Do you know any good place for beer near Oxford Street?
```

After the demo, prompt the user to submit their own text using the standard two-step flow.

> Do not collapse the demo into a summary such as "6 detections found". Show the actual script output blocks so the user can see the full workflow.

---

## Placeholder Policy

Use placeholders exactly as produced by the script. Do not invent or substitute different placeholder labels in responses. Consistency between the detection list and the final sanitized output is required for reviewer traceability.

---

## Audit Surfaces

The script exposes three reviewer-facing verification surfaces:

- **Default text output** — includes span offsets, local context, rule IDs, regex patterns, regex flags, and rationale per detection
- **`--format json`** — structured engine metadata with per-detection offsets, context, rationale, and regex provenance
- **`--list-rules`** — full local rule catalog for inspecting coverage and blind spots

---

## Limitations

- Detection is exhaustive by regex standards, not by semantic understanding.
- Name and organization heuristics can produce false positives.
- Text is not paraphrased — only matched spans are replaced with placeholders.
- The skill is intentionally model-free; it cannot infer context.
- Preservation decisions are always user-driven; the skill does not auto-decide which items to keep.
