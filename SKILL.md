---
name: local-text-anonymizer
description: Use when the user wants deterministic local text sanitization without any LLM or model dependency. This skill detects likely private information with exhaustive regex and rule-based patterns, presents a numbered review list to the user, lets the user preserve selected items by number, and returns sanitized text with placeholders.
---

# Regex Privacy Sanitizer

This skill implements a fully deterministic privacy-review workflow for free-form text. It does not use any hosted LLM, local LLM, embedding model, or classifier at runtime. Detection and replacement are done with regex and local heuristics only.

## Install First

If you are installing this skill, do not treat this `SKILL.md` file as the whole artifact.

This skill requires the companion runtime file `regex_privacy_sanitizer.py`, and the correct source of truth is the public GitHub repository:

- `https://github.com/erguteb/local-text-anonymizer`

The installation rule is simple:

1. Go to the public GitHub repo above.
2. Download or clone the repository root, not just `SKILL.md`.
3. Make sure `SKILL.md` and `regex_privacy_sanitizer.py` stay in the same folder.

If an agent only has `SKILL.md`, that agent has an incomplete artifact and should immediately fetch the full repository before trying to install or test anything.

This skill folder is self-contained. It requires only:

- `SKILL.md`
- `regex_privacy_sanitizer.py`

There are no runtime model downloads, no external API calls, and no extra service dependencies.

## Important

This skill is a **folder-based artifact**, not a standalone markdown file.

It will not install or run correctly from `SKILL.md` alone. The companion runtime file
`regex_privacy_sanitizer.py` must be present in the same folder.

Required files:

- `SKILL.md`
- `regex_privacy_sanitizer.py`

If another agent downloads only `SKILL.md`, that is an incomplete artifact.

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
2. Reply with a reviewer-friendly summary first:
   `In your text, I detected certain private information, here is all of them:`
3. Show the original text and an annotated version of it where each detected span is marked with its detection number.
4. Show a numbered private-information summary list where each number is clearly tied to the matched span.
5. Then show the full detector list with number, category, placeholder, confidence, and matched text.
6. Show a sanitized preview and an end-to-end before/after comparison.
7. Ask the user which numbers to preserve, if any.
8. Re-run sanitization preserving those detection numbers.
9. Return the final sanitized text, the original text for comparison, and a prompt inviting the user to try another input.

If nothing is detected, say so directly and return the original text unchanged.

For reviewer-facing verification, prefer the richer audit surfaces:

- default text output now includes reviewer audit notes, span offsets, local context, rule IDs, regex patterns, and regex flags
- `--format json` exposes structured engine metadata plus per-detection offsets, context, rationale, and regex provenance
- `--list-rules` prints the entire local rule catalog so a reviewer can inspect what the skill can and cannot detect

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

Reviewer rule catalog:

```bash
python3 regex_privacy_sanitizer.py --list-rules
```

## Installation Expectations

Another AI agent should be able to use this skill by downloading this folder as-is and reading
`SKILL.md`. The skill does not rely on any other local package in this repository.

## Source Repository

Canonical public repository:

- `https://github.com/erguteb/local-text-anonymizer`

If another agent installs this from GitHub, it should use the repository root, not a
`blob/.../SKILL.md` URL. The artifact is the folder, not just the markdown file.

Incorrect installation:

- downloading only `SKILL.md`
- using a `blob/.../SKILL.md` URL as if it were the full skill

Correct installation:

- clone the repository root
- keep `SKILL.md` and `regex_privacy_sanitizer.py` together in the same folder
- run the skill from that folder

Repository-root installation flow:

```bash
git clone https://github.com/erguteb/local-text-anonymizer
cd local-text-anonymizer
python3 regex_privacy_sanitizer.py --text "Contact Jane Doe at jane@example.com."
```

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

1. the original text
2. the annotated input showing what items `1..n` refer to
3. a short numbered summary of the private information detected
4. the full detector output
5. a before/after comparison block
6. a preserve-choice prompt
7. a second-pass sanitized result
8. a prompt inviting the user to try another text

The built-in demo should be shown explicitly in the artifact, not just described abstractly.

First-pass structure from the script:

```text
In your text, I detected certain private information, here is all of them:
Original text:
I am a 23 year old guy single in London. I just broke up with my girlfriend Lily. Do you know any good place for beer near Oxford Street?

Annotated input:
<<1:I am a 23 year old>> guy <<2:single>> <<3:in London>>. I just <<4:broke up>> with my <<5:girlfriend Lily>>. Do you know any good place for beer <<6:near Oxford Street>>?

Summary:
1. "I am a 23 year old" -> age expression
2. "single" -> relationship or private-life detail
...

Detailed detections:
1. category=age expression | placeholder=[AGE] | confidence=medium | matched_text="I am a 23 year old"
2. category=relationship or private-life detail | placeholder=[RELATIONSHIP_DETAIL] | confidence=low | matched_text="single"
...

Sanitized preview if all detected items are masked:
[AGE] guy [RELATIONSHIP_DETAIL] [LOCATION]. I just [RELATIONSHIP_DETAIL] with my [PERSON]. Do you know any good place for beer [LOCATION]?
```

When presenting the demo to the reviewer, make sure the reviewer can immediately see what `1..6` correspond to in the original sentence. The annotated-input block is mandatory because it removes ambiguity.

For the demo, the private-information summary should read like this:

1. age
2. relationship status
3. city/location context
4. breakup/private-life detail
5. person name
6. specific destination/location for the downstream recommendation query

Then ask clearly whether any item should be preserved. Use wording like:

```text
If you want to preserve any detected item, reply with its number(s).
For this demo, preserving item 6 is recommended because it keeps the useful place constraint.
```

This is why preserving item `6` is the recommended demo choice: it keeps the useful location
constraint for a later LLM or text-sharing task, while still masking the more sensitive personal details.

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

When showing the preserve example, say this explicitly:

```text
If I preserve the 6th item, the sanitized result becomes:
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
2. show you a numbered summary of the private information detected,
3. show you the full detected list with categories and matched spans,
4. let you choose which items to preserve,
5. return the sanitized text,
6. and show the original text for comparison.
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
Original text:
...

Annotated input:
...

Summary:
1. ...
2. ...

Detailed detections:
1. ...
2. ...

End-to-end comparison:
Before:
...

After:
...

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

1. the original text
2. the annotated input with numbered spans
3. a numbered summary of the private information detected
4. the detailed detected list
5. the before/after comparison
6. the preserve prompt
7. the sanitized text
8. a final prompt inviting the user to try another text

## Placeholder Policy

Use the placeholders produced by the script. Do not invent different placeholders in the response unless you also update the script. Consistency between the detection list and the final sanitized text matters.

## Limits

- This skill is exhaustive by regex standards, not by semantic understanding.
- Some heuristics, especially names and organizations, can produce false positives.
- This skill does not paraphrase text; it only replaces detected spans with placeholders.
- This skill is intentionally model-free at runtime.
- The preserve flow is user-driven; the skill does not decide on its own which private items should be kept.
