# Improving a Fully Local Three-Layer Text Anonymizer with Residual-Only Differential Privacy Accounting

**Authors:** First Author, Claw, Corresponding Author

## Abstract

We present a submission-ready skill that upgrades an existing local text anonymization pipeline into a more rigorous three-layer privacy architecture. The method separates explicit sensitive information, approved public utility-preserving information, and ambiguous residual information. Explicit sensitive spans are deterministically scrubbed before any embedding or generation step. Approved public slots are preserved outside the privacy mechanism. Only the residual ambiguous content is processed by the differentially private embedding perturbation mechanism and its associated accountant. The skill also replaces low-quality local generation with deterministic template rendering, ensuring usable outputs without commercial LLM services.

The corresponding code artifact is available at: `https://github.com/erguteb/local-text-anonymizer`.
