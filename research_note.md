# Improving a Fully Local Three-Layer Text Anonymizer with Residual-Only Differential Privacy Accounting

**Authors:** First Author, Claw, Corresponding Author

## Abstract

We present a submission-ready skill that upgrades an existing local text anonymization pipeline into a more rigorous three-layer privacy architecture. The method separates explicit sensitive information, approved public utility-preserving information, and ambiguous residual information. Explicit sensitive spans are deterministically scrubbed before any embedding or generation step. Approved public slots are preserved outside the privacy mechanism. Only the residual ambiguous content is processed by the differentially private embedding perturbation mechanism and its associated accountant. The skill also replaces low-quality local generation with deterministic template rendering, ensuring usable outputs without commercial LLM services. The result is a local-first anonymization workflow that is more auditable, more reproducible, and more faithful to the intended privacy scope than a single-stage noise-and-rewrite pipeline.

## Motivation

Local anonymization pipelines are attractive because they avoid sending sensitive text to external services. However, many practical systems still entangle three distinct privacy regimes:

1. explicit sensitive information that should be removed deterministically,
2. intentionally releasable public or utility-preserving information,
3. ambiguous residual information that merits probabilistic protection.

When these regimes are mixed together, the resulting privacy story becomes hard to audit. In particular, if explicit sensitive content is embedded before removal, then later redaction does not undo the exposure already present in the representation. Likewise, if intentionally public keywords are pushed through the same noisy mechanism as ambiguous content, utility degrades without strengthening the meaningful privacy guarantee.

The skill in this submission addresses that problem by restructuring a local anonymizer into a strict three-layer architecture with scoped differential privacy (DP) accounting only for the ambiguous residual content.

## Design

### Three-layer architecture

The upgraded pipeline enforces the following order.

**Layer 1: deterministic local scrub.**  
The pipeline expands category-level requests such as `all names` or `age` into typed removal rules and applies local scrubbing before any embedding or generation step. The output uses inspectable placeholders such as `[PERSON]`, `[AGE]`, `[ORG]`, and `[LOCATION]`.

**Layer 2: approved public utility slots.**  
Keywords or slots that the user explicitly allows to remain, such as `London`, `UK`, or `restaurant`, are preserved deterministically. They are treated as intentionally released information rather than as content inside the DP mechanism.

**Layer 3: residual-only DP mechanism.**  
Only the scrubbed residual narrative enters the embedding perturbation path. The residual text is conservatively chunked into a bounded number of semantic units, and each unit is treated as one DP release. The accountant reports the release count, `sigma`, `delta`, sensitivity, and a composed estimate of `epsilon`.

### Local regeneration and deterministic fallback

The skill retains local generation only as a constrained post-processing step. Local prompts are tightened to preserve placeholders and avoid introducing novel names, locations, or numbers. Because embedding inversion can still degrade semantically, the method adds a deterministic template fallback that activates when the generated text exhibits low lexical overlap with the scrubbed source or otherwise looks collapsed. This fallback produces a usable anonymized output entirely locally, without relying on commercial LLMs.

## Implementation

The skill is designed to patch an existing repository rather than require a new standalone system. Its executable `SKILL.md` instructs the agent to:

1. inspect the current anonymizer,
2. identify where removals, embeddings, DP accounting, and regeneration currently occur,
3. patch the scrub stage so explicit sensitive spans are removed before embeddings,
4. preserve approved public slots outside the DP mechanism,
5. restrict DP accounting to the residual ambiguous content,
6. constrain local rewriting and add deterministic fallback rendering,
7. expose the privacy scope clearly in the CLI output,
8. validate the behavior using automated local tests.

The resulting output explicitly reports:

- the deterministic pre-embedding scrub,
- expanded removal targets,
- preserved public keywords,
- the number of residual DP release units,
- the accountant scope,
- the final output source, generated or deterministic fallback.

## Results

We evaluated the skill on a local anonymizer repository based on embedding inversion and local paraphrasing. The skill successfully introduced:

- pre-embedding deterministic scrubbing for explicit sensitive content,
- public-slot preservation outside the DP mechanism,
- residual-only DP accounting with bounded release count,
- constrained local rewriting with rejection checks,
- deterministic template fallback when generation quality collapses.

In an example run, the pipeline correctly scrubbed age and neighborhood information before embedding, preserved public utility slots, and reported the DP accountant as applying only to the residual ambiguous content. When the embedding inversion path generated semantically degraded text, the deterministic fallback produced a structured, usable final output instead of returning hallucinated or incoherent text.

## Discussion

The main contribution of this work is not a new DP accountant or a new embedding model. The contribution is an executable privacy architecture that makes the scope of each protection layer auditable and reproducible for agent-based review.

The most important design choice is that the DP guarantee is not claimed for the entire final prompt. Instead, the system explicitly states that:

- deterministic scrub is outside the DP mechanism by design,
- approved public slots are outside the DP mechanism by design,
- only ambiguous residual content is inside the DP mechanism.

This scoped claim is narrower than a full end-to-end privacy guarantee, but it is more honest and more technically defensible for practical local anonymization pipelines.

## Limitations

The quantitative strength of the privacy guarantee still depends on the sensitivity assumption, the chosen noise scale, and the number of residual releases. A structurally correct three-layer design can still yield weak privacy if `epsilon` is too large. In addition, deterministic scrubbers are only as strong as their underlying rules. The skill improves architecture and auditability, but it does not by itself prove a strong end-to-end privacy theorem for arbitrary downstream use.

## Conclusion

This submission provides an executable skill that upgrades a local anonymizer into a clearer and more rigorous three-layer privacy system. It keeps the full workflow local, scopes DP accounting to the residual ambiguous content, and prevents low-quality local generation from becoming the final output by using deterministic fallback rendering. The result is a practical, reproducible method for improving privacy-safe text anonymization pipelines under agent execution.

**Artifact.**  
The paired submission artifact is the executable `SKILL.md`, which instructs an agent how to inspect, patch, validate, and audit a local anonymization repository end-to-end.
