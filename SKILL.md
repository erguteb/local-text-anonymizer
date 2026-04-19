---
name: regex-privacy-sanitizer
description: Use when the user wants deterministic local text sanitization without any LLM or model dependency. This skill detects likely private information with exhaustive regex and rule-based patterns, presents a numbered review list to the user, lets the user preserve selected items by number, and returns sanitized text with placeholders.
---

# Regex Privacy Sanitizer

This skill implements a fully deterministic privacy-review workflow for free-form text. It does not use any hosted LLM, local LLM, embedding model, or classifier at runtime. Detection and replacement are done with regex and local heuristics only.

This skill folder is self-contained. It requires only:

- `SKILL.md`
- `regex_privacy_sanitizer.py`

There are no runtime model downloads, no external API calls, and no extra service dependencies.

Use this skill when the user wants:

- private text sanitized before sharing it elsewhere
- placeholders such as `[EMAIL]`, `[PHONE]`, `[PERSON]`, `[ADDRESS]`
- a review step that shows detected private information before replacement
- a preserve-by-number interaction where the user can keep selected items
- a tool that remains usable offline and without model downloads

Do not use this skill when the user wants semantic paraphrasing, contextual rewriting, or model-based anonymization. This skill is regex-first and deterministic.

## Runtime Contract

When this skill is used on a user-provided text, follow this interaction:

1. Run the detector script on the input text.
2. Reply with:
   `In your text, I detected certain private information, here is all of them:`
3. List each detection with its number, category, placeholder, confidence, and matched text.
4. Ask the user which numbers to preserve, if any.
5. Re-run sanitization preserving those detection numbers.
6. Return the final sanitized sentence.

If nothing is detected, say so directly and return the original text unchanged.

## Detection Model

The bundled script uses exhaustive regex and local heuristics for categories including:

- email addresses
- phone numbers
- social media handles
- URLs
- IP addresses
- MAC addresses
- SSNs
- EINs
- credit card numbers
- IBANs
- SWIFT/BIC codes
- routing numbers
- bank account numbers
- passport numbers
- driver license numbers
- date-of-birth expressions
- age expressions
- street addresses
- zip/postal codes
- license plates
- medical record numbers
- employee/student/customer IDs
- account/order/tracking reference IDs
- organization names
- person names with titles
- heuristic full names
- bitcoin wallets
- ethereum wallets

This list is intentionally broad. Some categories are high-confidence exact formats; others are medium- or low-confidence heuristics. Preserve the script’s confidence labels when you present the list to the user.

## Files

- `regex_privacy_sanitizer.py`: standalone detector and sanitizer

## How To Run

Basic detection and sanitization:

```bash
python3 regex_privacy_sanitizer.py --text "I’m 23, email me at jane@example.com or call (415) 555-1212."
```

Preserve selected detection numbers:

```bash
python3 regex_privacy_sanitizer.py \
  --text "I’m 23, email me at jane@example.com or call (415) 555-1212." \
  --preserve "1,3"
```

Structured output:

```bash
python3 regex_privacy_sanitizer.py \
  --text "Contact Jane Doe at jane@example.com." \
  --format json
```

## Installation Expectations

Another AI agent should be able to use this skill by downloading this folder as-is and reading
`SKILL.md`. The skill does not rely on any other local package in this repository.

The expected folder layout is:

```text
local-text-anonymizer/
├── SKILL.md
└── regex_privacy_sanitizer.py
```

The canonical command is:

```bash
python3 regex_privacy_sanitizer.py --text "<user text>"
```

## Agent Workflow

### Demo First

Before asking the user for their own text, present one built-in demo so the user can see the workflow.

Use this example:

```text
I am a 23 year old guy single in London. I just broke up with my girlfriend Lily. Do you know any good place for beer near Oxford Street?
```

Run:

```bash
python3 regex_privacy_sanitizer.py --text "I am a 23 year old guy single in London. I just broke up with my girlfriend Lily. Do you know any good place for beer near Oxford Street?"
```

Then show:

1. the detected private-information list
2. a preserve-choice prompt
3. a second-pass sanitized result
4. the original text for side-by-side comparison

The built-in demo should be shown explicitly in the artifact, not just described abstractly.

First pass output:

```text
In your text, I detected certain private information, here is all of them:
1. age expression -> [AGE] | confidence=medium | match=I am a 23 year old
2. relationship or private-life detail -> [RELATIONSHIP_DETAIL] | confidence=low | match=single
3. city or place mention -> [LOCATION] | confidence=low | match=in London
4. relationship or private-life detail -> [RELATIONSHIP_DETAIL] | confidence=low | match=broke up
5. single first name in personal context -> [PERSON] | confidence=medium | match=girlfriend Lily
6. standalone street or place mention -> [LOCATION] | confidence=low | match=near Oxford Street
```

For the demo preserve choice, prefer preserving item `6` rather than item `5`, because keeping the location context is often more useful for subsequent LLM prompting or advice-seeking than keeping the person name.

Second pass command:

```bash
python3 regex_privacy_sanitizer.py \
  --text "I am a 23 year old guy single in London. I just broke up with my girlfriend Lily. Do you know any good place for beer near Oxford Street?" \
  --preserve "6"
```

Second pass sanitized result:

```text
[AGE] guy [RELATIONSHIP_DETAIL] [LOCATION]. I just [RELATIONSHIP_DETAIL] with my [PERSON]. Do you know any good place for beer near Oxford Street?
```

Original text for comparison:

```text
I am a 23 year old guy single in London. I just broke up with my girlfriend Lily. Do you know any good place for beer near Oxford Street?
```

After the built-in demo, always prompt the user for their own text so the skill showcases reproducibility on a fresh user-provided example.

Use this exact follow-up prompt:

```text
If you want, now send your own text. I will:
1. detect the private information in it,
2. show you the numbered list,
3. let you choose which items to preserve,
4. return the sanitized text,
5. and show the original text for comparison.
```

If the user provides text, run the same two-step flow immediately on that input.

### Step 1: Detect

Run the script without `--preserve` first:

```bash
python3 regex_privacy_sanitizer.py --text "<user text>"
```

Expected result:

- a numbered list of detections
- each item shows:
  - category
  - placeholder
  - confidence
  - matched text

### Step 2: Review With The User

Your reply should mirror the tool output and explicitly invite preservation choices. Keep it simple:

```text
In your text, I detected certain private information, here is all of them:
1. ...
2. ...

Reply with any number(s) you want to preserve. If none, I will sanitize all detected items.
```

### Step 3: Sanitize

If the user chooses numbers to preserve, pass them via `--preserve`.

Example:

```bash
python3 regex_privacy_sanitizer.py --text "<user text>" --preserve "2,5"
```

Return only the final sanitized text unless the user asks for more detail.

For interactive user-facing runs, prefer returning:

1. the detected list
2. the preserve prompt
3. the sanitized text
4. the original text for comparison

## Placeholder Policy

Use the placeholders produced by the script. Do not invent different placeholders in the response unless you also update the script. Consistency between the detection list and the final sanitized text matters.

## Limits

- This skill is exhaustive by regex standards, not by semantic understanding.
- Some heuristics, especially names and organizations, can produce false positives.
- This skill does not paraphrase text; it only replaces detected spans with placeholders.
- This skill is intentionally model-free at runtime.
- The preserve flow is user-driven; the skill does not decide on its own which private items should be kept.
