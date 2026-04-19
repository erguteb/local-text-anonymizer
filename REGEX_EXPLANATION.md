# Regex Explanation

This file explains the regex and rule-based patterns used by `regex_privacy_sanitizer.py`.

It is **documentation only**. It is not part of the runtime contract of the skill and does not
need to be read for the skill to operate correctly.

## Design Goal

The detector is intentionally:

- deterministic
- local-only
- model-free at runtime
- broad in coverage, even at the cost of some false positives

The script uses two mechanisms:

1. exact or near-exact regex patterns for structured identifiers
2. heuristic regex patterns for softer categories such as names and organizations

Each detection is assigned:

- a `category`
- a `placeholder`
- a `confidence` level (`high`, `medium`, `low`)

## Confidence Philosophy

### High confidence

Used when the format is relatively distinctive, for example:

- email addresses
- phone numbers
- SSNs
- IP addresses
- passport-number phrases
- date-of-birth phrases

### Medium confidence

Used when the pattern is common enough to be useful but can still overmatch:

- organization names
- addresses
- age expressions
- account/routing references

### Low confidence

Used when the pattern is intentionally broad and may produce false positives:

- heuristic full names

## Pattern Inventory

### Email addresses

Regex:

```regex
\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b
```

Purpose:
- detect standard email forms like `name@example.com`

### Phone numbers

Regex:

```regex
(?:(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w))
```

Purpose:
- detect common North-American-style numbers
- allow optional country code and punctuation

### Social handles

Regex:

```regex
(?<!\w)@[A-Za-z0-9_]{2,32}\b
```

Purpose:
- detect handles such as `@user_name`

### URLs

Regex:

```regex
\b(?:https?://|www\.)\S+\b
```

Purpose:
- detect web links

### IP addresses

Regex:

```regex
\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b
```

Purpose:
- detect IPv4 addresses

### MAC addresses

Regex:

```regex
\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b|\b(?:[0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}\b
```

Purpose:
- detect colon- or hyphen-separated MAC addresses

### SSNs

Regex:

```regex
\b\d{3}-\d{2}-\d{4}\b
```

Purpose:
- detect US Social Security number formatting

### EINs

Regex:

```regex
\b\d{2}-\d{7}\b
```

Purpose:
- detect US Employer Identification Number formatting

### Credit card numbers

Regex:

```regex
\b(?:\d[ -]*?){13,19}\b
```

Purpose:
- broadly detect card-like digit strings

Note:
- the raw regex is intentionally broad, but the script then applies a Luhn checksum filter
- long digit strings that fail Luhn should not survive as card detections

### IBANs

Regex:

```regex
\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b
```

Purpose:
- detect IBAN-style banking identifiers

### SWIFT/BIC

Regex:

```regex
\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b
```

Purpose:
- detect SWIFT/BIC bank codes when they appear with explicit banking context such as:
  - `swift code ABCDEF12`
  - `bic ABCDEF12`
  - `bank code ABCDEF12`

### Routing numbers

Regex:

```regex
\b(?:routing|aba)\s*(?:number|#|no\.?)?\s*[:#-]?\s*\d{9}\b
```

Purpose:
- detect routing-number phrases

### Bank account numbers

Regex:

```regex
\b(?:account|acct)\s*(?:number|#|no\.?)\s*[:#-]?\s*[A-Z0-9-]{6,20}\b
```

Purpose:
- detect account-number phrases

Note:
- this now requires an explicit marker such as `account number`
- plain prose like `the account closed yesterday` should no longer match

### Passport numbers

Regex:

```regex
\bpassport\s*(?:number|#|no\.?)?(?:\s+is)?\s*[:#-]?\s*[A-Z0-9]{6,12}\b
```

Purpose:
- detect passport-number statements such as `passport number is A1234567`

### Driver license numbers

Regex:

```regex
\b(?:driver'?s?|driving|dl)\s*license\s*(?:number|#|no\.?)?\s*[:#-]?\s*[A-Z0-9-]{5,20}\b
```

Purpose:
- detect license-number phrases

### Date of birth

Regex:

```regex
\b(?:dob|date of birth|born on|birth date)\s*[:#-]?\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|[A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{2,4})\b
```

Purpose:
- detect DOB phrases and common date formats

### Age expressions

Regex:

```regex
\b(?:age\s*\d{1,3}|\d{1,3}\s*(?:years old|year-old)|i\s*[\'’]?m\s*\d{1,3}|i am\s*\d{1,3})\b
```

Purpose:
- detect age-like expressions such as:
  - `age 23`
  - `23 years old`
  - `I'm 23`
  - `I am 23`

### Street addresses

Regex:

```regex
\b\d{1,6}\s+(?:[A-Z][a-z0-9.'-]*\s+){0,5}(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl|Terrace|Ter)\b\.?
```

Purpose:
- detect common street-address forms

### Zip or postal codes

Regex:

```regex
\b\d{5}(?:-\d{4})?\b|\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b
```

Purpose:
- detect plain 5-digit US ZIP codes
- detect ZIP+4 codes
- detect some UK-style postal codes

### License plates

Regex:

```regex
\b(?:license plate|plate)\s*[:#-]?\s*[A-Z0-9-]{4,10}\b
```

Purpose:
- detect explicit plate-number phrases

### Medical record numbers

Regex:

```regex
\b(?:mrn|medical record|patient id)\s*(?:number|#|no\.?)?\s*[:#-]?\s*[A-Z0-9-]{4,20}\b
```

Purpose:
- detect healthcare-style record identifiers

### Employee or student IDs

Regex:

```regex
\b(?:employee|student|staff|customer|client)\s*(?:id|number|#|no\.?)\s*[:#-]?\s*[A-Z0-9-]{3,20}\b
```

Purpose:
- detect internal or institutional identifiers

### Account, order, booking, or ticket IDs

Regex:

```regex
\b(?:account|order|booking|reservation|tracking|invoice|case|ticket)\s*(?:(?:id|number|#|no\.?)\s*[:#-]?\s*|\s+)(?=[A-Z0-9-]{3,24}\b)(?:[A-Z]*\d[A-Z0-9-]*|\d[A-Z0-9-]{2,23})\b
```

Purpose:
- detect operational reference identifiers such as:
  - `order 12345678`
  - `order number 12345678`
  - `ticket ABC-123`

Note:
- this now requires the identifier-like token to contain at least one digit
- plain prose like `order pizza` should no longer match

### Organization names

Regex:

```regex
\b[A-Z][\w&'.-]+(?:\s+[A-Z][\w&'.-]+){0,4}\s+(?:Inc|LLC|Ltd|Corp|Corporation|Company|Co\.|Studio|Agency|University|Hospital|Bank)\b
```

Purpose:
- detect organization names with common suffixes

### Person names with titles

Regex:

```regex
\b(?:Mr|Mrs|Ms|Miss|Dr|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b
```

Purpose:
- detect titled personal names

### Heuristic full names

Regex:

```regex
\b(?!(?:Contact|Call|Email|Text|Meet|Visit|Reach|Message|Thanks|Dear)\b)[A-Z][a-z]{1,20}\s+[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20})?\b
```

Purpose:
- detect simple multi-word capitalized names

Warning:
- this is still broad and can match non-name capitalized phrases
- a small stop-list is used to avoid obvious sentence-leading verbs such as `Contact`
- a second place-name filter is applied to suppress common location phrases such as `New York`

### Cryptocurrency wallets

Bitcoin regex:

```regex
\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b
```

Ethereum regex:

```regex
\b0x[a-fA-F0-9]{40}\b
```

Purpose:
- detect common wallet address formats

## Post-Detection Logic

After regex matching, the script applies two extra cleanup stages.

### 1. Deduplication

Repeated matches with the same span, placeholder, and text are merged.

### 2. Overlap resolution

Overlapping detections are resolved by preferring:

- earlier spans
- longer spans
- higher confidence when span length is equal

This helps avoid double replacement of the same text region.

### 3. Category-specific plausibility filters

Some categories are validated after regex matching:

- credit cards must pass a Luhn checksum
- low-confidence full-name detections are filtered against a small place-name list

## Sanitization Logic

Once the user chooses which detection numbers to preserve, the script:

1. removes any chosen IDs from the replacement set
2. replaces remaining spans with their placeholders
3. keeps all other text unchanged
4. lightly normalizes punctuation spacing

In text mode, the script is intentionally detect-first:

1. first run without `--preserve`: prints the numbered detection list only
2. second run with `--preserve` (or with no detections): prints the sanitized text

If `--preserve` contains invalid non-numeric items, the CLI exits with a normal argparse usage
error instead of a raw Python exception.

## Known Limitations

- Regex can overmatch or undermatch.
- The name and organization patterns are intentionally aggressive.
- The script does not infer context semantically.
- It does not resolve entity coreference.
- It does not paraphrase around replacements; it only substitutes placeholders.

These tradeoffs are intentional because the runtime system must remain deterministic, local, and model-free.
