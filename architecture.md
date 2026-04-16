# Local Anonymizer Improvement Architecture

## Goal

Improve an existing local anonymizer so it:
- runs fully locally,
- removes explicit sensitive content deterministically,
- preserves approved utility slots without unnecessary distortion,
- applies DP accounting only to ambiguous residual information,
- uses local constrained regeneration instead of unconstrained repair,
- rejects outputs that leak or hallucinate.

## Recommended Design

### 1. Pre-classify input content

Split content into three buckets:
- explicit sensitive content: deterministically scrub or replace,
- approved public or utility-preserving content: keep as fixed slots,
- ambiguous residual content: protect with DP.

This classification should happen before embedding or generation.

### 2. Deterministic scrubber

Use local-only detectors:
- regex for phones, emails, URLs, dates, ages, money, ids
- typed location patterns
- local NER or heuristic NER for people, organizations, and places
- user-provided category removals such as `all names`, `all ages`, `all employers`

Output typed placeholders rather than vague replacements.

### 3. Safe-slot extraction

Extract allowed fields and preserve them as structured values. Typical slots:
- task
- approved geography
- tone or preference tags
- allowed product/category/topic keywords

Do not perturb these slots if they are intentionally public.

### 4. Residual DP mechanism

Build the residual text by removing or abstracting the other two buckets.

Recommended approach:
- combine related sentences into a small number of semantic blocks,
- embed the residual blocks,
- perturb each residual block embedding,
- account for each perturbed block as one DP release,
- invert or summarize those blocks locally,
- reassemble with fixed safe slots.

If the release count is too high, the design is wrong. Reduce the number of residual releases.

## Accounting Position

The rigorous position is:
- Layer 1 deterministic scrub is not covered by DP and does not need to be.
- Layer 2 safe-slot preservation is not covered by DP because it is intentionally released.
- Layer 3 residual release is the DP mechanism and must be fully accounted for.

This is stronger and clearer than claiming DP over the whole prompt while also preserving large public chunks verbatim.

## Regeneration Strategy

Avoid free-form "make it natural" prompts.

Prefer one of:
- slot-filling template
- compact JSON schema then render
- constrained rewrite that preserves placeholders and approved slots exactly

Minimum rules for local generation:
- no new entities,
- no new numbers,
- no new locations,
- preserve placeholders,
- keep response short,
- if generation fails, fall back to deterministic template output.

## Patch Priorities For Existing Repos

1. Move sensitive-span removal ahead of embedding.
2. Replace category-blind literal replacement with typed removal rules.
3. Replace naive sentence splitting with a real segmenter.
4. Gate expensive comparison/baseline paths behind a true optional flag.
5. Change paraphrase prompts so the model is not asked to invent coherence from corrupted text.
6. Add rejector checks for named entities, numbers, and banned spans.
7. Report DP scope explicitly in CLI output.

## Testing Guidance

Use short local fixtures that exercise:
- typed name removal,
- age removal,
- public-city preservation,
- safe keyword preservation,
- residual-only DP accounting,
- failure fallback to deterministic templating,
- hallucination rejection.

## Opinionated Recommendation

If the existing inversion path remains unstable, do not insist on inverting the full residual into fluent prose. A better local system is often:
- deterministic scrub,
- extract safe slots,
- DP-protect a compressed residual summary,
- render the final anonymized prompt from a template.

That is less flashy than full generative repair, but it is usually more defensible.
