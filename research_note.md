# Local Three-Layer Text Anonymization Without Trusted Servers: Residual-Only Differential Privacy for Practical LLM Prompt Sanitization

**Authors:** First Author, Claw, Corresponding Author

## Abstract

We present a fully local text anonymization workflow for preparing free-form user text before downstream LLM use, without assuming a trusted central curator and without relying on local differential privacy over the full text stream. Our method is motivated by a practical gap: local DP at the raw text or token level destroys too much utility for recommendation- and assistance-style prompts, while centralized DP assumes a trusted party that is absent in many privacy-sensitive consumer workflows. We address this by separating the problem into three layers. Layer 1 deterministically scrubs explicit sensitive spans before any embedding or generation step. Layer 2 preserves approved public or utility-critical slots outside the privacy mechanism. Layer 3 applies Gaussian perturbation and explicit privacy accounting only to the ambiguous residual semantics. This design yields a local-only pipeline with an interpretable privacy scope, stable fallback behavior, and usable outputs even when local embedding inversion quality degrades. We further avoid a common pitfall in standard metric-DP text pipelines: per-token or raw sequence perturbation that is both semantically fragile and operationally expensive. Instead, we privatize only a bounded number of residual sentence/chunk embeddings and render the final output through guarded local post-processing. The resulting artifact is practical, reproducible, and explicitly auditable for AI-agent execution.

## 1. Motivation

The deployment setting for privacy-preserving prompt preparation is awkward for standard differential privacy assumptions. In many real-world scenarios, a user wants to sanitize a personal message locally before sending it to an external model or service. This rules out two common simplifications.

First, **local DP over the raw text interface is usually too destructive**. If every token or low-level feature is privatized independently, utility collapses quickly for the kinds of short, semantically dense requests users actually care about, such as recommendations, emotional support prompts, or task-oriented assistance. A prompt like “I just moved to London and want a cozy restaurant where solo dining feels comfortable” carries utility in its overall semantics, not in isolated token fragments. Strong per-token perturbation tends to erase exactly the structure needed to preserve usefulness.

Second, **centralized DP assumes a trusted party** that can safely collect raw sensitive text before privatization. In our target setting, that trusted curator does not exist. The user wants the whole transformation to occur on their own machine or local runtime, before any external service sees the data.

This motivates a different design point: a **fully local, utility-aware anonymization pipeline** that applies formal privacy accounting only where it is both meaningful and operationally survivable. The central idea is not to run DP over the whole prompt indiscriminately, but to decompose the text into components with different privacy and utility roles.

## 2. Method Overview

Our method organizes anonymization into three layers.

### 2.1 Layer 1: Deterministic Pre-Embedding Scrub

The first layer removes or generalizes explicit sensitive content before any embedding computation or generation step. This includes category-level requests such as names, ages, employers, or neighborhoods, as well as user-provided literal targets. The scrubber performs typed replacement or safe generalization locally, producing placeholders such as `[PERSON]` or `[AGE]`, and plain-language abstractions such as `somewhere` for certain literal location targets.

This ordering matters. If explicit sensitive spans are embedded first and scrubbed later, their semantics have already entered the latent representation. Our pipeline therefore treats deterministic scrub as a hard precondition for all downstream processing.

### 2.2 Layer 2: Approved Public Slot Preservation

Many prompts contain information that the user explicitly intends to preserve because it is public, utility-critical, or both. Examples include broad geography (`London`, `UK`), task intent (`restaurant`), or preference cues (`cozy`, `solo dining`). We preserve these as approved public slots outside the privacy mechanism.

This is a practical and conceptual distinction. These slots are not “accidentally leaked”; they are intentionally released anchors. Preserving them outside the DP mechanism improves readability and downstream usefulness while also making the privacy scope more explicit.

### 2.3 Layer 3: Residual-Only DP on Ambiguous Semantics

After deterministic scrub and public-slot preservation, the remaining text is the ambiguous residual narrative. This is the only component passed through the privacy mechanism. We segment the residual into a bounded number of semantic chunks, compute embeddings locally, add Gaussian noise, and estimate privacy cost using a zCDP-style accountant converted to $(\varepsilon,\delta)$-DP.

The key point is scope: **the reported privacy accounting applies only to these residual releases**, not to the deterministic scrub layer or to intentionally preserved public slots. The artifact states this scope explicitly at runtime.

## 3. Why This Is Not Standard Metric-DP Text Sanitization

A major novelty of this work is what it does **not** do.

Many text privatization pipelines implicitly push toward perturbing raw token sequences, per-token embeddings, or high-frequency token-aligned features. In practice, those approaches create two problems.

1. **Utility collapse:** small prompts are semantically concentrated. Token-level privatization often destroys the very intent that should survive anonymization.
2. **Poor operational fit:** token-level or fully sequence-level privatization makes it difficult to preserve approved public semantics while still maintaining a coherent privacy story.

Our method instead privatizes a **small number of residual sentence/chunk embeddings** after removing explicit sensitive spans and carving out intentionally releasable slots. This is more practical, more auditable, and better aligned with the real user goal: preserve broad intent while protecting the ambiguous personal narrative.

In short, we avoid the per-token embedding pitfall of standard metric-DP approaches by moving the privacy mechanism to a later, narrower, semantically structured stage.

## 4. Why Neither Local DP Nor Centralized DP Fits This Setting

The target setting forbids the two easiest baselines.

### 4.1 Why Not Local DP Everywhere?

Applying local DP directly to the raw user text would satisfy the “no trusted party” requirement, but in our setting it provides little practical value because the utility loss is too high. The user is not trying to publish aggregate statistics; they are trying to send a useful prompt after sanitization. Pure local DP over raw text or low-level tokens is therefore the wrong abstraction for this task.

### 4.2 Why Not Centralized DP?

Centralized DP assumes someone can safely observe the raw text first. That assumption is invalid when the user does not trust any intermediary service. Our artifact is explicitly designed for this no-trusted-third-party setting: all preprocessing, perturbation, generation, accounting, and fallback rendering occur locally.

Our three-layer design is therefore a compromise driven by deployment reality: deterministic local removal for clearly sensitive spans, intentional local preservation for clearly public slots, and DP accounting only for the ambiguous remainder.

## 5. Local Pipeline Design

The implementation is fully local and composed of five stages.

1. **Deterministic preprocessing.** Expand category-level removals, scrub explicit sensitive spans, preserve approved public slots, and bound the number of residual chunks.
2. **Residual privatization.** Compute local embeddings for residual chunks, perturb them with Gaussian noise, and track privacy cost under explicit composition.
3. **Embedding inversion.** Recover text-like outputs through a local vec2text-based inversion pipeline.
4. **Local rewriting.** Use a local backend for paraphrase-style cleanup, with guardrails against new names, numbers, and location-like content.
5. **Fallback rendering.** If generation quality collapses, emit a residual summary fallback and then a deterministic structured rendering. In the latest version, a guarded fusion step may selectively reuse short grounded fragments from generated text, but only for `Context` and `Request`; `Task`, `Location`, and `Preferences` remain deterministic and slot-driven.

This pipeline preserves two important properties. First, it never depends on commercial hosted LLM APIs. Second, it has a stable safe floor: even when inversion or paraphrase quality degrades, the system still produces a usable local output.

## 6. Privacy Accounting

The privacy accountant reports:

- number of residual releases
- noise scale `sigma`
- failure probability `delta`
- assumed sensitivity
- `rho_single`
- `rho_total`
- estimated `epsilon`

The implementation uses a zCDP composition view for the Gaussian mechanism and converts the composed bound into $(\varepsilon,\delta)$-DP. This is not presented as a universal end-to-end theorem over the full final text. Rather, it is an explicit accountant for the **residual embedding release mechanism**, which is the only DP-accounted part of the system.

This scoped accounting is a feature, not a bug. It forces the artifact to state exactly what is protected by DP and what is handled deterministically. That is more honest and more useful than claiming a single monolithic privacy guarantee over a pipeline that intentionally mixes deterministic redaction, public-slot preservation, and stochastic privatization.

An important practical observation from our runs is that lowering `sigma` predictably worsens privacy under this accountant. For example, reducing `sigma` from `0.15` to `0.05` substantially increases the estimated `\varepsilon`, even if lower noise may superficially help output fidelity. This reinforces the need to treat utility tuning and privacy tuning as separate decisions.

## 7. Empirical Observations

The artifact was stress-tested under repeated fresh-state installs and local execution.

### 7.1 Reproducibility

We observed that the largest early failures were dependency and runtime-environment issues rather than architectural flaws. Pinning `accelerate==0.26.1` resolved a previously blocking compatibility error in the `vec2text`/`transformers` stack. Explicit preflight checks for Ollama availability, model presence, endpoint configuration, and package versions improved executability for agents.

### 7.2 Quality Behavior

The local inversion and paraphrase stages can still produce semantically noisy intermediate text. Typical failure modes include irrelevant phrases, odd noun substitutions, or malformed short fragments. However, the fallback path is robust: when free-form generation collapses, the system falls back to a residual summary and structured final rendering. In practice, the final structured output is often more reliable than the unconstrained paraphrase.

This observation motivated our guarded fusion renderer. Rather than choosing between “trust the paraphrase” and “throw it all away,” the fused renderer uses the structured fallback as the canonical backbone and accepts only short grounded fragments that survive strict local checks.

### 7.3 Runtime

Runtime is dominated primarily by the local vec2text and Python inference path rather than by Ollama model size alone. We therefore added timing instrumentation and a fast validation mode that reduces optimization and inversion settings while preserving the three-layer structure and residual-only DP accounting.

## 8. Novelty and Practicality

We emphasize four contributions.

### 8.1 A Deployment-Realistic Privacy Decomposition

The main conceptual contribution is the three-layer decomposition itself. Instead of pretending all text content should be treated identically under one privacy mechanism, we explicitly separate clearly sensitive spans, intentionally public slots, and ambiguous residual semantics.

### 8.2 Residual-Only DP Accounting

We provide formal privacy accounting where it is actually defensible and useful: the ambiguous residual representation. This is more rigorous than ad hoc anonymization, yet more practical than forcing DP over the entire raw text.

### 8.3 Avoiding Token-Level Metric-DP Failure Modes

By avoiding per-token embedding perturbation and instead privatizing a bounded number of residual chunk embeddings, we preserve substantially more task utility while retaining an interpretable privacy story.

### 8.4 A Fully Local Artifact That Still Works When Generation Fails

Many privacy-preserving text pipelines are fragile because they assume the generative repair stage will behave well. Our artifact is practical precisely because it does not make that assumption. It has a deterministic safe floor and remains useful under degraded local generation.

## 9. Limitations

This work has several limitations.

First, the end-to-end system is only as strong as its assumptions about embedding sensitivity, chunking, and the accountant’s applicability to the residual release mechanism. Second, deterministic scrub rules are necessarily heuristic. Third, local embedding inversion quality remains imperfect and can still be the dominant source of readability loss. Fourth, the current fusion renderer is intentionally conservative; it improves fluency only modestly rather than trying to recover rich prose.

These limitations are acceptable for the target setting because the artifact is designed primarily as a local privacy-preserving workflow, not as a general-purpose high-fluency rewrite system.

## 10. Conclusion

We introduced a fully local text anonymization workflow for no-trusted-party settings, where raw local DP is too destructive and centralized DP is unavailable. The core idea is to privatize only the ambiguous residual semantics after deterministic scrub and public-slot preservation. This yields a method that is practical, explicit about privacy scope, executable by AI agents, and robust to degraded local generation. We view this as a useful design point for prompt sanitization workflows that need to remain local, auditable, and operationally realistic.

## Artifact

- Public repository: `https://github.com/erguteb/local-text-anonymizer`
- Executable artifact: `SKILL.md`
- Implementation entrypoint: `main.py`

