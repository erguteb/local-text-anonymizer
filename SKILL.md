# Local Anonymizer Improvement

## Purpose

This skill upgrades a local text anonymization pipeline into a stricter three-layer privacy architecture and validates that the resulting system remains fully local.

The target architecture is:

1. **Layer 1: deterministic scrub before embeddings**
   Remove or generalize explicit sensitive information locally before any embedding or generation step.
2. **Layer 2: approved public slot preservation**
   Preserve user-approved public or utility-preserving information outside the privacy mechanism.
3. **Layer 3: DP protection for ambiguous residual content**
   Apply embedding perturbation and privacy accounting only to the residual ambiguous content.

This skill is designed for repositories that already contain a local anonymizer and need to be hardened rather than rewritten from scratch.

## Included files

- `main.py`: the Python implementation corresponding to this skill
- `SKILL.md`: this execution guide
- `requirements.txt`: tested dependency versions for this artifact

## Source repository

The corresponding public repository is:

- `REPO_URL=https://github.com/erguteb/local-text-anonymizer`
- `REPO_COMMIT=fefbdc65f27523fe0c7adc9ef1a770f5e54c8063`

If this skill is evaluated from a fresh environment, clone the repository first and then run the bundled or repository `main.py`.

```bash
git clone https://github.com/erguteb/local-text-anonymizer
cd local-text-anonymizer
git checkout fefbdc65f27523fe0c7adc9ef1a770f5e54c8063
python3 -m py_compile main.py
```

## Required runtime assumptions

- Python 3 is installed.
- The skill runs locally only.
- If Ollama is used, a compatible local Ollama server is running at the configured endpoint and the chosen model is already available.
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

## What the code should do

The final pipeline must satisfy all of the following:

- explicit sensitive information is scrubbed before embeddings
- approved public keywords are preserved outside the DP mechanism
- only ambiguous residual content is counted by the DP accountant
- local rewriting is constrained to avoid invented names, numbers, and location-like content
- low-quality generated text first falls back to a residual summary and then to structured final rendering
- the runtime output explicitly states the DP scope

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

### Step 3: run a representative local example

Before the representative example, run preflight first and verify that the configured
`--ollama-base-url` is reachable and that the requested model is available locally. Only run
the full Ollama example if preflight confirms that the intended endpoint is available. If
Ollama is unavailable, skip this example and use the smoke test plus code inspection as the
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

Only after those succeed should you run the full example below.

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
  --no-interactive-removal
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
- if generation quality collapses, the pipeline emits:
  - a residual summary fallback output
  - a structured final output built from the preserved public slots

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

### Step 8: confirm deterministic fallback behavior

Check that when generation quality collapses, the pipeline emits a two-stage fallback:

1. a residual summary fallback that stays close to the scrubbed residual text
2. a structured final rendering built from the residual summary plus the preserved public slots

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

## Acceptance criteria

This skill succeeds only if all of the following are true:

- the whole anonymization process remains local
- Layer 1 deterministic scrub happens before embeddings
- Layer 2 approved public slots are preserved outside DP
- Layer 3 residual ambiguous content is the only DP-accounted mechanism
- the accountant is reported explicitly
- bad generated text is replaced by deterministic fallback output

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
