# Local Anonymizer Improvement

## Purpose

This skill implements and validates a fully local three-layer text anonymization workflow for free-form user prompts. It is self-contained: the skill defines the privacy model, the execution path, the expected runtime behavior, and the verification steps for the bundled `main.py`.

The skill’s job is to run a local anonymization pipeline that:

1. deterministically scrubs explicit sensitive spans before any embedding step
2. preserves approved public or utility-critical slots outside the privacy mechanism
3. applies DP-style perturbation and explicit privacy accounting only to the ambiguous residual content
4. uses only local models and local services
5. produces a stable final output even when free-form generation quality collapses

The privacy architecture is:

1. **Layer 1: deterministic scrub before embeddings**
   Remove or generalize explicit sensitive information locally before any embedding or generation step.
2. **Layer 2: approved public slot preservation**
   Preserve user-approved public or utility-preserving information outside the privacy mechanism.
3. **Layer 3: DP protection for ambiguous residual content**
   Apply embedding perturbation and privacy accounting only to the residual ambiguous content.

## What This Skill Does

This skill is not just a test wrapper. It defines how to execute `main.py` as a local privacy pipeline and how to interpret its stages.

At runtime, `main.py` does the following:

1. reads the private input text from `--text`
2. reads approved public slots from `--keywords`
3. reads explicit sensitive removals from `--remove-info`
4. performs deterministic pre-embedding scrub
5. preserves approved public slots separately from the DP mechanism
6. perturbs only the residual ambiguous text representation and reports DP accounting for that scope
7. locally reconstructs and rewrites the residual text
8. if generation quality is poor, falls back to a residual summary and then to a guarded structured renderer

This means the skill is both:

- an executable artifact: it tells the agent exactly how to run the code
- a method definition: it tells the agent what privacy behavior the code is supposed to implement

## How Public and Private Information Are Combined

The skill uses a deliberate separation between private and public information.

- Private information:
  - the original user text passed through `--text`
  - explicit sensitive spans that should be removed or generalized
  - ambiguous residual narrative content that is protected by the DP-accounted mechanism
- Public or approved information:
  - keywords passed through `--keywords`
  - utility-preserving slots such as broad location, task type, or preference style

The code does **not** simply mix public and private text together and then anonymize everything at once.

Instead it does this:

1. scrub explicit sensitive content from the private text
2. redact approved public slots out of the residual text so they are not privatized unnecessarily
3. apply the DP-accounted embedding perturbation only to the remaining residual content
4. restore approved public slots later in the final rendering
5. allow only guarded fusion of safe generated fragments into `Context` and `Request`
6. return both:
   - a structured output without public-information fusion
   - a structured output with approved public-information fusion

`Task`, `Location`, and `Preferences` remain slot-driven and deterministic. This is the core reason the skill can preserve utility while keeping the privacy scope explicit.

## Included files

- `main.py`: the Python implementation corresponding to this skill
- `SKILL.md`: this execution guide
- `requirements.txt`: tested dependency versions for this artifact

## Source repository

The corresponding public repository is:

- `REPO_URL=https://github.com/erguteb/local-text-anonymizer`
- `REPO_COMMIT=7c3d975ff4b8f36ba9e3b216babc1b827ed53e26`

If this skill is evaluated from a fresh environment, clone the repository first and then run the bundled or repository `main.py`.

```bash
git clone https://github.com/erguteb/local-text-anonymizer
cd local-text-anonymizer
git checkout 7c3d975ff4b8f36ba9e3b216babc1b827ed53e26
python3 -m py_compile main.py
```

## Required runtime assumptions

- Python 3 is installed.
- The skill runs locally only.
- If Ollama is used, a compatible local Ollama server is running at the configured endpoint and the chosen model is already available.
- The vec2text anonymization path also requires local Hugging Face checkpoints. If those checkpoints are missing from the local cache, the full representative anonymization run may require a one-time model download before it can complete.
- No commercial LLM service is used at any point in the anonymization flow.

## Ollama setup

If you want to use the Ollama backend, do not assume Ollama is already installed, running, or
bound to `http://127.0.0.1:11434`.

For a typical Linux machine, the primary setup flow is:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama --version
ollama serve
ollama pull qwen3.5:latest
curl -s http://127.0.0.1:11434/api/tags
```

Do these in order:

1. install Ollama
2. verify the `ollama` binary exists
3. start the Ollama server
4. pull the required model
5. verify the endpoint with `/api/tags`
6. only then run the full skill example

If the `ollama` command is missing, install Ollama first with:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

If `ollama serve` is not already running in another terminal/session, start it before running the
representative example. A normal Linux workflow is:

```bash
ollama serve
```

Then, in another shell:

```bash
ollama pull qwen3.5:latest
curl -s http://127.0.0.1:11434/api/tags
```

Expected result from `/api/tags`:

- the request succeeds
- the returned model list includes `qwen3.5:latest`

Use `http://127.0.0.1:11434` only if a local Ollama server is actually running there. If your
environment uses a different local endpoint, start Ollama for that environment and pass the
correct value via `--ollama-base-url`.

If Ollama is unavailable in your environment, use the smoke test and preflight path and treat
the full Ollama example as optional.

## Environment setup

Create a local Python environment and install the required dependencies before running the artifact.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Do not replace these pinned versions with floating package names. The artifact contains a
transformers monkey-patch that requires `transformers==4.37.2`, and the pinned set in
`requirements.txt` is the tested environment for this skill. In particular, `accelerate` is
also pinned because newer 1.x releases can break the vec2text / transformers stack used here.

If your environment restricts network access, preflight must also confirm that the required
vec2text/Hugging Face checkpoints are already present in the configured local cache. Ollama
readiness alone is not enough for the full anonymization path.

## Canonical entrypoint

Run:

```bash
python3 main.py --help
```

The skill assumes `main.py` is the artifact entrypoint unless you intentionally rename it and update this file.
The guaranteed local smoke test is:

```bash
python3 -m py_compile main.py
```

This smoke test does not require Ollama or model downloads.

## What `main.py` Must Implement

The final pipeline must satisfy all of the following:

- explicit sensitive information is scrubbed before embeddings
- approved public keywords are preserved outside the DP mechanism
- only ambiguous residual content is counted by the DP accountant
- local rewriting is constrained to avoid invented names, numbers, and location-like content
- low-quality generated text first falls back to a residual summary, then optionally through guarded fusion, and finally to two structured outputs: one without public fusion and one with public fusion
- the runtime output explicitly states the DP scope

In other words, `main.py` is the implementation of the skill’s algorithm, not an unrelated helper script. The skill definition and `main.py` should agree on:

- what counts as private input
- what counts as approved public data
- where the DP accountant applies
- how the final rendered output is assembled

## Execution workflow

### Step 1: verify the artifact entrypoint

Run:

```bash
source .venv/bin/activate
python3 -m py_compile main.py
python3 main.py --preflight --llm-backend ollama --paraphrase-model "qwen3.5:latest"
python3 main.py --help
```

Expected result:

- the syntax smoke test passes
- preflight reports the pinned package versions
- preflight reports the pinned `accelerate` version as part of the compatibility contract
- preflight prints the configured `--ollama-base-url`
- preflight prints the configured vec2text cache directory
- preflight reports the required vec2text/Hugging Face model ids
- preflight reports whether those local checkpoints are already present or missing
- if required local checkpoints are missing, preflight marks the full anonymization path as blocked until those assets are available locally
- preflight reports whether the `ollama` binary is installed locally
- if Ollama is reachable at that configured endpoint, preflight reports:
  - endpoint reachable
  - locally available models
  - whether the requested model is present or missing
- if the requested model is missing, preflight tells the agent to run `ollama pull <model>`
- the CLI loads successfully
- the runtime flags include privacy controls such as:
  - `--remove-info`
  - `--keywords`
  - `--sigma`
  - `--max-privacy-chunks`
  - `--skip-baseline`

### Step 2: inspect whether the pipeline is truly three-layer

Read the code paths in `main.py` that implement:

- preprocessing or scrub logic
- keyword preservation
- privacy chunking
- DP accounting
- local rewrite logic
- deterministic fallback rendering

Expected result:

- Layer 1 occurs before embedding inversion
- Layer 2 is intentionally preserved
- Layer 3 is the only DP-accounted mechanism

### Step 3: run a reduced-runtime local validation example

Before the representative example, run preflight first and verify that the configured
`--ollama-base-url` is reachable and that the requested model is available locally. Only run
the full Ollama example if preflight confirms that the intended endpoint is available. If
Ollama is unavailable, or if preflight reports missing vec2text/Hugging Face checkpoints, skip this example and use the smoke test plus code inspection as the
local validation path.

For a normal Linux machine, the intended Ollama-ready sequence is:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

Then, from another shell:

```bash
ollama pull qwen3.5:latest
curl -s http://127.0.0.1:11434/api/tags
source .venv/bin/activate
python3 main.py --preflight --llm-backend ollama --paraphrase-model "qwen3.5:latest"
```

Only after those succeed should you run the reduced-runtime validation example below.

Preflight must also report the vec2text/Hugging Face assets as locally available. If preflight
reports missing checkpoints, populate the local cache first. A network-restricted environment
cannot complete the representative anonymization run until those assets already exist locally.

Use `--fast` for the first end-to-end validation pass. This mode is the preferred smoke
validation path because the full vec2text inversion and correction pipeline can be slow on a
CPU-only or lightly provisioned local machine. In `--fast` mode the script keeps the same
three-layer privacy structure and residual-only DP accounting, but reduces expensive local
work by:

- using fewer joint embedding optimization steps
- using fewer vec2text recursive inversion steps
- using a single paraphrase call instead of sentence-by-sentence paraphrasing
- skipping the no-keyword baseline path
- skipping the final embedding audit, which is evaluation-only and does not affect the output

Run:

```bash
source .venv/bin/activate
python3 main.py \
  --text "I’m 23, just moved to London for work, and my flat in Shoreditch feels empty after a breakup. I want a cozy restaurant tonight where dining alone feels comfortable." \
  --keywords "restaurant, UK, London, cozy, solo dining" \
  --remove-info "all names, age, Shoreditch" \
  --sigma 0.15 \
  --max-privacy-chunks 2 \
  --llm-backend ollama \
  --paraphrase-model "qwen3.5:latest" \
  --ollama-base-url "http://127.0.0.1:11434" \
  --skip-baseline \
  --no-interactive-removal \
  --fast
```

Use `http://127.0.0.1:11434` only if a local Ollama server is actually running there. If your
environment exposes Ollama on a different local endpoint, pass that endpoint via
`--ollama-base-url`.

If preflight says the endpoint is reachable but the model is missing, pull the model first:

```bash
ollama pull qwen3.5:latest
```

Then rerun preflight before the full example.

Expected result:

- the output prints a deterministic pre-embedding scrub
- the output prints expanded removal targets
- the output prints preserved public keywords
- the output prints residual DP release units
- the output prints a DP accountant with scope restricted to residual ambiguous content only
- the three privacy layers remain intact in fast mode; only runtime-heavy local evaluation work is reduced
- if generation quality collapses, the pipeline emits:
  - a residual summary fallback output
  - a structured final output without public fusion
  - a fusion-guarded structured final output with public fusion
- the output prints a stage timing summary so the reviewer can see where runtime is spent

### Step 3b: run the full heavyweight example only if needed

If you need the full research-style path rather than a smoke validation run, rerun the same
command without `--fast`. Expect this to take materially longer, especially when vec2text
model loading, inversion, and correction are running on CPU.

### Step 4: confirm Layer 1 behavior

Look for a preprocessing stage that:

- expands category requests like `all names` and `age`
- applies local typed replacements such as:
  - `[PERSON]`
  - `[AGE]`
  - `[ORG]`
  - `[LOCATION]`
- may generalize literal location targets into plain-language placeholders such as `somewhere`
- produces a scrubbed text before embedding

Expected result:

- explicit sensitive data does not reach the embedding step in raw form

### Step 5: confirm Layer 2 behavior

Check that approved public slots such as:

- `London`
- `UK`
- `restaurant`
- `cozy`
- `solo dining`

are preserved outside the DP mechanism and reused in final rendering.

Expected result:

- utility-preserving slots remain deterministic and are not unnecessarily distorted

### Step 6: confirm Layer 3 behavior

Check that:

- the residual text is segmented into a bounded number of chunks
- each chunk is counted as one release
- the accountant reports:
  - `num_releases`
  - `sigma`
  - `delta`
  - `sensitivity`
  - `epsilon_estimate`

Expected result:

- the accountant scope is printed as residual ambiguous content only

### Step 7: confirm local rewrite constraints

Check that the local rewrite stage rejects candidates that:

- introduce new names
- introduce new numbers
- introduce new locations or other location-like terms
- have very low semantic overlap with the scrubbed source

Expected result:

- degraded inversion text is not accepted silently

### Step 8: confirm guarded fallback behavior

Check that when generation quality collapses, the pipeline emits:

1. a residual summary fallback that stays close to the scrubbed residual text
2. a guarded fusion step that may reuse only safe grounded fragments from the generated text
3. a structured final rendering without public-slot fusion
4. a structured final rendering with approved public-slot fusion

The structured rendering should contain:

- scrubbed text
- public slots
- deterministic labels such as:
  - `Context`
  - `Request`
  - `Task`
  - `Location`
  - `Preferences`

Expected result:

- the final output remains usable and local, even when inversion quality is poor
- `Task`, `Location`, and `Preferences` remain deterministic and slot-driven
- `Context` and `Request` may be lightly enriched only when candidate fragments survive local safety and grounding checks
- the runtime exposes both variants so the agent can compare residual-only rendering against public-slot-fused rendering

### Step 9: run local regression tests

Run:

```bash
source .venv/bin/activate
python3 -m py_compile main.py
python3 main.py --help
```

The preferred regression command is:

```bash
source .venv/bin/activate
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The included public tests should validate at minimum:

- category-level pre-scrub expansion
- privacy chunk limiting
- rewrite hallucination rejection
- deterministic fallback activation

Expected result:

- the CLI loads locally without import errors
- the pinned dependency environment is consistent with the artifact
- the public tests pass locally
- the reduced-runtime `--fast` example is the default validation path for end-to-end checks

## Acceptance criteria

This skill succeeds only if all of the following are true:

- the whole anonymization process remains local
- Layer 1 deterministic scrub happens before embeddings
- Layer 2 approved public slots are preserved outside DP
- Layer 3 residual ambiguous content is the only DP-accounted mechanism
- the accountant is reported explicitly
- bad generated text is constrained by guarded fusion and ultimately replaced by deterministic fallback structure when needed

## Output audit summary

After running the workflow, produce a final summary with these fields:

- `local_only`
- `layer1_deterministic_scrub_before_embedding`
- `layer2_public_slots_outside_dp`
- `layer3_residual_only_dp_scope`
- `dp_accounting_reported`
- `deterministic_fallback_present`
- `remaining_limitations`

## Limitations

- This skill improves privacy architecture and auditability; it does not by itself prove a full end-to-end privacy theorem.
- Quantitative privacy strength still depends on the configured noise scale, sensitivity assumption, and number of residual releases.
- Deterministic scrub quality depends on the strength of the local rules.
- The representative example requires a reachable local Ollama server and a locally available model.
- `http://127.0.0.1:11434` is only the default local Ollama endpoint example; other local environments may require a different `--ollama-base-url`.
- The full non-`--fast` representative example can be slow because vec2text inversion and correction are compute-heavy local steps.
