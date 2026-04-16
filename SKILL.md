---
name: local-anonymizer-improve
description: Use when the user wants to improve, redesign, or implement a fully local text anonymization pipeline with deterministic PII scrubbing, utility-preserving safe slots, and rigorous DP accounting for ambiguous residual information. Trigger for requests about hardening local anonymizers, replacing commercial LLM anonymization, adding privacy accounting, or restructuring a three-layer anonymization design.
---

# Local Anonymizer Improve

Use this skill when working on a local-first anonymizer or privacy-safe prompt-preparation pipeline. The goal is not "rewrite everything with a local LLM." The goal is to separate information classes, apply deterministic protection to explicit sensitive content, preserve approved public utility slots, and reserve DP-style perturbation for the ambiguous residual content.

Default opinion:
- Keep the whole process local.
- Apply explicit removal before embeddings, not after.
- Use DP only for ambiguous residual semantics, not for already-public safe slots and not for explicit sensitive spans that should be deterministically removed.
- Prefer schema-constrained regeneration plus rejection checks over free-form paraphrasing.

If the repo already has a "three-layer" anonymizer, improve it toward that architecture instead of replacing it wholesale.

## Workflow

1. Inspect the current pipeline and identify where it currently handles:
   - explicit sensitive spans,
   - public or approved utility-preserving information,
   - ambiguous residual information,
   - privacy accounting,
   - post-processing and verification.
2. Classify failure modes:
   - sensitive info enters embeddings before scrub,
   - public information is unnecessarily noised,
   - DP accountant is mathematically weak or misapplied,
   - free-form local LLM repair invents facts,
   - chunking multiplies releases and explodes epsilon,
   - validation only checks fluency and not leakage.
3. Refactor toward the target architecture:
   - deterministic typed scrubber first,
   - safe-slot/template preservation second,
   - DP perturbation on residual ambiguous content third,
   - local constrained regeneration fourth,
   - local leakage/readability verification last.
4. Validate with local-only test cases.
5. Report the privacy assumptions, what is and is not covered by DP, and any remaining failure modes.

## Target Architecture

Use these layers in this order.

### Layer 1: Deterministic Removal For Explicit Sensitive Content

This layer is for information the user wants removed or generalized with high confidence.

Examples:
- names
- ages
- exact addresses
- contact details
- employers
- account numbers
- neighborhood or street-level location
- dates tied to identity

Implementation guidance:
- Prefer local regex, typed rules, dictionaries, and local NER over generative rewriting.
- Replace with typed placeholders such as `[PERSON]`, `[AGE]`, `[EMPLOYER]`, `[NEIGHBORHOOD]`.
- Keep this step inspectable and testable.
- Do not rely on literal string replacement alone if the request is category-level, such as "all names" or "all ages".

### Layer 2: Safe Public Utility Slots

This layer is for information the user explicitly allows to remain because it is needed for downstream usefulness.

Examples:
- task type: `restaurant recommendations`
- coarse geography: `London`, `UK`
- allowed preferences: `cozy`, `solo dining`, `good food`

Implementation guidance:
- Treat these as a whitelist or template fields.
- Preserve them deterministically.
- Do not send them through the DP perturbation path unless the user specifically wants them obfuscated too.

### Layer 3: DP Protection For Ambiguous Residual Information

This layer is for information that is not clearly public but also not an explicit must-remove field.

Examples:
- broad life context
- vague emotional or situational narrative
- residual semantics after typed scrub and safe-slot extraction

Implementation guidance:
- Extract only the residual text after Layers 1 and 2.
- Chunk conservatively; fewer releases are better.
- Apply embedding perturbation only to this residual representation.
- Invert or regenerate only this residual part.
- Reassemble with the deterministic safe slots afterwards.

This is the part that should carry the formal DP accounting.

## Privacy Accounting Requirements

Be explicit about the accounting assumptions. If the repo claims DP, require it to state:
- sensitivity model,
- release unit,
- number of releases,
- sigma,
- delta,
- composition rule,
- what content is in scope for the guarantee.

Preferred rule for this style of pipeline:
- deterministic explicit scrub is outside the DP mechanism,
- safe-slot preservation is outside the DP mechanism,
- only the residual ambiguous-content release is counted by the DP accountant.

Practical guidance:
- Minimize `num_releases`.
- If sentence-wise chunking causes large `epsilon`, reduce chunk count or move to fewer semantic blocks.
- Warn when `epsilon > 10`; treat that as weak privacy.
- Explain that the DP guarantee only covers the release mechanism and its assumptions, not downstream human interpretation or implementation bugs.

If the current repo applies DP to the full raw text embedding, challenge that design unless there is a strong reason.

## Local-Only Regeneration

Do not use commercial LLM services.

Allowed approaches:
- local Ollama models,
- local Hugging Face models,
- deterministic non-LLM reconstruction where practical.

Preferred generation style:
- schema-constrained or template-constrained rewrite,
- placeholder preservation,
- no new names, numbers, or locations unless they are whitelisted,
- reject outputs that invent facts or leak removed attributes.

When a local paraphraser is used, prefer prompts that say:
- preserve placeholders exactly,
- do not introduce named entities,
- do not add numbers,
- keep approved slots,
- rewrite only the residual text into a short neutral summary.

Avoid open-ended prompts like "make this sound natural" when the source text is already degraded.

## Validation Checklist

Run local validation for each candidate output:
- no banned spans remain,
- no new named entities appear outside whitelist,
- no new numeric attributes appear unless allowed,
- placeholders remain intact,
- output is semantically usable,
- DP report is printed for the residual mechanism,
- leakage/readability checks are reported separately.

If the repo has tests, add cases for:
- typed removals such as "all names" and "age",
- public-slot preservation,
- low-release accounting,
- rejection of hallucinated rewrites,
- fallback to deterministic templated output when generation quality collapses.

## Implementation Heuristics

- Replace naive `text.split(".")` chunking with a proper sentence or semantic segmenter.
- Prefer typed removal before any embedding call.
- Keep a strict boundary between deterministic scrubbed spans, public slots, and DP-protected residual content.
- If a baseline/comparison path is expensive, gate it behind a real debug flag so production runs do not pay for it.
- When privacy and utility conflict, preserve utility via deterministic safe slots and spend the DP budget only on the residual narrative.

## References

Read [architecture.md](references/architecture.md) when you need the fuller design rationale, implementation map, and patch priorities for an existing repo.
