# PrivateKickOff: Offline, LLM-Free PII Removal for Personal Agentic Prompt Pipelines

**Authors:** Ergute Bao, Hongyan Chang, and Ali Shahin Shamsabadi

## Abstract

We present a practical local skill for privacy sanitization of free-form text using exhaustive regex and rule-based heuristics only. Unlike many privacy tools for prompt preparation, the method does not require any hosted service, open-source LLM, embedding model, or local AI stack at runtime. The skill detects likely private information, presents a numbered review list to the user, allows the user to preserve selected items, and then returns a sanitized text with explicit placeholders. This design is intentionally simple but useful: it has minimal operational dependencies, executes offline, and gives the user direct control over the privacy-utility tradeoff. The main contribution is not novelty in machine learning, but an executable, low-friction method that covers a broad range of structured and narrative-sensitive private information while remaining transparent, inspectable, and easy to adopt in downstream prompt pipelines or text-sharing workflows.

## 1. Motivation

There is a large practical gap between privacy-sensitive text workflows and deployable privacy tools. Many users want to sanitize text before sharing it with another party or before using it as a prompt for a downstream LLM. In practice, however, many anonymization pipelines require either remote services or local model stacks that increase setup complexity, computational overhead, and failure surface.

Our goal in this work is narrower but highly practical: provide a **fully local, minimal-dependency privacy sanitization skill** that can be executed by an AI agent or a user on an ordinary machine with only Python available. The design requirement is strict:

- no hosted API
- no local LLM
- no embedding model
- no model downloads
- deterministic behavior

This pushes the method toward regex and rule-based heuristics. That choice is deliberate. In many operational settings, especially prompt preparation, a transparent and low-friction detector with user review is preferable to a semantically richer but much heavier model-based stack.

## 2. Problem Setting

We consider the following setting:

1. A user provides a free-form text.
2. The system detects likely private information spans.
3. The user reviews the detections and may preserve selected items.
4. The system outputs a sanitized version with placeholders.
5. The sanitized text can then be shared directly or used as input to a subsequent LLM.

This setting has two properties that matter.

First, **utility matters**: the user may want to preserve some information because it remains necessary for the downstream task. Second, **operational simplicity matters**: requiring a local model stack often defeats adoption in exactly the environments where lightweight local privacy tools are most useful.

## 2.1 Related Work

Our work sits at the intersection of privacy-preserving NLP, text sanitization, and classical de-identification. A large line of recent work studies **differentially private text sanitization** by perturbing words, tokens, or semantically related substitutes. Representative examples include SANTEXT-style natural text sanitization (Yue et al., Findings of ACL 2021), CusText (Chen et al., Findings of ACL 2023), TEM for metric-DP text privatization (Carvalho et al., 2023), and more recent MLDP-based systems such as CluSanT and DYNTEXT. These methods are important because they provide formal privacy mechanisms, but they also expose the tradeoff that motivates our skill: if privacy is enforced through token-level perturbation, utility can degrade rapidly for short prompts, user-authored narratives, and recommendation-style queries. In practice, perturbing token by token often changes exactly the lexical material that makes a prompt useful downstream.

Metric-DP methods partly address this by moving from surface tokens to **embedding-space neighborhoods**, but that creates a different dependency: utility then relies on having a good embedding model and a meaningful distance geometry. In other words, metric-DP is not “free privacy”; it inherits the quality and domain fit of the embedding model itself. This is explicit in recent work on metric differential privacy for text and sentence embeddings, including TEM and later sentence-embedding mechanisms such as CMAG. For our target setting, this is a poor fit. We want a sanitizer that remains usable when there is no trusted model stack, no network access, no GPU, and no appetite for downloading or maintaining open-source NLP models.

Our design therefore intentionally returns to **old-school regex and rule-based de-identification**. This is not because regex is universally superior, but because it occupies a different point in the design space: minimal dependency, transparent behavior, and extremely fast editability. Classical NLP and privacy work has long shown that rule-based systems remain competitive in domains with stable textual formats, especially in de-identification of clinical narratives and other compliance-sensitive text. Rule-based and hybrid systems remain central reference points in that literature; see, for example, Grouin and Zweigenbaum (2013), Dehghan et al. (2015), and recent reviews of clinical free-text de-identification. Our contribution is to transplant that operational logic into prompt sanitization and personal-text sharing workflows, while keeping the interaction loop user-facing and utility-aware.

This also distinguishes our skill from broader privacy frameworks such as Microsoft Presidio. Presidio is a more general ecosystem with separate analyzer and anonymizer components, richer anonymization operators, and optional integration with NLP models and external services. Our goal is narrower: a cold-start, self-contained, regex-only skill that performs both detection and placeholder replacement locally, with a built-in preserve-by-number review loop. In settings where minimal setup, offline execution, and rapid rule patching matter more than framework breadth, this narrower design is a practical advantage.

A practical advantage of this choice is maintainability. Regex rules are easy to patch, extend, and audit, and modern AI coding tools are unusually good at searching pattern gaps, proposing new rules, and updating detectors quickly. That means the artifact can evolve rapidly without requiring retraining, re-hosting, or model re-evaluation. In our view, this is a real scientific and engineering contribution for agent-executable privacy tooling: not just a sanitizer that works once, but a sanitizer whose detection surface can be iteratively improved at very low operational cost.

## 3. Method

The skill is implemented as a deterministic Python script plus an executable `SKILL.md`.

### 3.1 Detection

The detector uses a large inventory of regex and local heuristic rules for categories including:

- email addresses
- phone numbers
- URLs and handles
- IP and MAC addresses
- SSNs, EINs, routing numbers, account numbers
- passport and driver-license expressions
- dates of birth and age expressions
- street addresses and postal codes
- medical and institutional identifiers
- account, order, booking, invoice, ticket, and tracking references
- organization names
- person names
- cryptocurrency wallet formats
- narrative-sensitive cues such as relationship-status details, breakup language, single personal names, and location mentions

The detector assigns each match:

- a category
- a placeholder
- a confidence label

This is important for user review because the skill deliberately accepts some lower-precision heuristics in exchange for broader coverage.

### 3.2 Replacement

After detection, the system does not immediately hide everything without user control. Instead, it lists all detections in numbered form and asks the user which items to preserve. Only the unpreserved detections are replaced with placeholders such as `[EMAIL]`, `[PHONE]`, `[PERSON]`, or `[LOCATION]`.

This design improves practical utility. A user may want to keep some information because it remains necessary for the subsequent prompt or for text sharing, while still masking the rest.

### 3.3 Post-Detection Filtering

Although the detector is regex-driven, it is not purely raw pattern matching. Some categories use additional plausibility filters. For example:

- card-like numeric spans must pass a Luhn checksum before they are treated as credit cards
- place-name filters reduce some person-name false positives
- overlap resolution ensures that one private span is not redundantly or inconsistently masked by multiple competing rules

This matters for both precision and false-negative control. When a private format is detectable by a rule, the system should have a low chance of missing it because another overlapping rule interfered. The overlap-resolution stage helps avoid exactly that kind of masking conflict.

## 4. Contribution

We make four practical contributions.

### 4.1 Minimal-Dependency Privacy Sanitization

The skill requires no open-source LLM or AI model at runtime. This sharply lowers adoption friction and makes the skill robust in offline or resource-constrained environments.

### 4.2 Executable User Review Loop

The method explicitly integrates a preserve-by-number review stage. This is important because privacy-sensitive text sanitization is rarely binary: some information should be removed, but some may need to remain for downstream usefulness. The skill gives the user direct control over that choice.

### 4.3 Broad Regex Coverage With Transparent Behavior

The detector covers both structured identifiers and some narrative-sensitive cues. The rules are inspectable, editable, and documented. This transparency is itself a practical contribution for agent execution and auditing.

### 4.4 Better Utility for Subsequent Prompting or Sharing

Because the user can preserve selected items, the sanitized output is often more useful for downstream LLM prompting or text sharing than a one-shot full redaction system. The skill does not attempt to optimize semantic fluency; instead, it optimizes controllable redaction under minimal infrastructure.

## 5. Technical Rationale

A natural criticism of regex-heavy systems is that they are brittle. That is true in the abstract, but the deployment setting here changes the tradeoff.

The goal is not semantic understanding of every sentence. The goal is a low-cost first-pass privacy filter that can be executed anywhere. In that setting, regex has three advantages:

1. **determinism**: identical inputs produce identical detections
2. **inspectability**: every detection can be traced to a concrete rule
3. **low dependency surface**: no model installation, no GPU, no download latency, no inference server

The skill intentionally accepts some false positives, especially for low-confidence name and location heuristics, because the user review stage exists to correct them. By contrast, a silent false negative is harder for the user to notice. In this sense, the method is biased toward recall with explicit review rather than toward hidden under-detection.

We also emphasize an operational point: if a private pattern is rule-detectable, then careful overlap handling reduces the chance that conflicting regex rules cause it to be left unmasked. This is not a formal guarantee, but it is an important engineering property of the implementation.

More precisely, once a category is covered by an implemented regex family, the system’s failure modes are dominated by **coverage gaps** rather than stochastic decoding or model drift. The detector does not sample, approximate, or depend on latent semantics at runtime. This means that for rule-detectable patterns, false negatives can be pushed down primarily by extending the rule inventory and by resolving overlaps so that one matched category does not accidentally suppress another. That is a very different error model from model-based sanitizers, where misses can arise from representation quality, calibration, decoding choices, or domain shift.

## 6. Demo Workflow

The skill includes a built-in demo before asking for the user’s own text. The demo text is:

> I am a 23 year old guy single in London. I just broke up with my girlfriend Lily. Do you know any good place for beer near Oxford Street?

The intended agent-facing demo is:

1. run the detector on the demo text
2. show the numbered detection list
3. ask whether the user wants to preserve any items
4. run the sanitizer on the second pass
5. show the sanitized text and the original text for comparison

After the demo, the skill asks whether the user wants another demo on their own input and repeats the same review loop.

This built-in example is not cosmetic. It demonstrates the actual interaction contract of the skill and helps another agent execute it correctly without hidden assumptions.

## 7. Limitations

This work has obvious limitations.

First, regex cannot recover true semantic meaning. Second, some low-confidence heuristics are intentionally broad and may over-detect names or locations. Third, the current system replaces spans with placeholders rather than paraphrasing around them, so readability may degrade in heavily redacted sentences.

These limitations are acceptable for our target use case because the method is not meant to optimize semantic elegance, nor is it intended to be a fully rigorous research-level anonymization system in the sense of model-based semantic rewriting or formally end-to-end privacy guarantees. Its value is different: it is a handy, low-friction skill with minimal dependencies that can run almost anywhere, be inspected easily, and be patched quickly. That makes it useful for auditing, for first-pass privacy review, and as a strong baseline against which more advanced anonymization techniques can be compared. In other words, the contribution is not “best possible anonymization quality,” but a practical privacy tool that is easy to execute, reason about, and improve incrementally.

## 8. Conclusion

We present a practical local privacy-sanitization skill that uses exhaustive regex and rule-based heuristics instead of model-based anonymization. Its core value is not sophistication of representation learning, but **practical executability**: it runs anywhere, requires almost no setup, gives the user explicit control over preservation choices, and produces outputs that are useful for downstream LLM prompting or text sharing. In settings where dependency minimization and transparent behavior matter more than semantic fluency, this is a strong design point.

## Artifact

- Skill file: `SKILL.md`
- Implementation: `regex_privacy_sanitizer.py`
- Regex reference: `REGEX_EXPLANATION.md`

## References

- Xiang Yue, Minxin Du, Tianhao Wang, Yaliang Li, Huan Sun. *Differential Privacy for Text Analytics via Natural Text Sanitization*. Findings of ACL-IJCNLP 2021. https://aclanthology.org/2021.findings-acl.337/
- Sai Chen, Fengran Mo, Yanhao Wang, Cen Chen, Jian-Yun Nie, Chengyu Wang, Jamie Cui. *A Customized Text Sanitization Mechanism with Differential Privacy*. Findings of ACL 2023. https://aclanthology.org/2023.findings-acl.355/
- Ricardo Silva Carvalho, Theodore Vasiloudis, Oluwaseyi Feyisetan, Ke Wang. *TEM: High Utility Metric Differential Privacy on Text*. 2023. https://www.amazon.science/publications/tem-high-utility-metric-differential-privacy-on-text
- *A Metric Differential Privacy Mechanism for Sentence Embeddings*. ACM Transactions on Privacy and Security, 2025. DOI: 10.1145/3708321
- Ahmed Musa Awon, Yun Lu, Shera Potka, Alex Thomo. *CluSanT: Differentially Private and Semantically Coherent Text Sanitization*. NAACL 2025. https://aclanthology.org/2025.naacl-long.187/
- Juhua Zhang, Zhiliang Tian, Minghang Zhu, Yiping Song, Taishu Sheng, Siyi Yang, Qiunan Du, Xinwang Liu, Minlie Huang, Dongsheng Li. *DYNTEXT: Semantic-Aware Dynamic Text Sanitization for Privacy-Preserving LLM Inference*. Findings of ACL 2025. https://aclanthology.org/2025.findings-acl.1038/
- Cyril Grouin, Pierre Zweigenbaum. *Automatic de-identification of French clinical records: comparison of rule-based and machine-learning approaches*. Stud Health Technol Inform, 2013. https://pubmed.ncbi.nlm.nih.gov/23920600/
- Azad Dehghan, Aleksandar Kovacevic, George Karystianis, John A. Keane, Goran Nenadic. *Combining knowledge- and data-driven methods for de-identification of clinical narratives*. Journal of Biomedical Informatics, 2015. https://pubmed.ncbi.nlm.nih.gov/26210359/
- *De-identification of clinical free text using natural language processing: A systematic review of current approaches*. Artificial Intelligence in Medicine, 2024. https://doi.org/10.1016/j.artmed.2024.102845
