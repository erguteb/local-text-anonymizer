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
- If Ollama is used, a local Ollama server is running and the chosen model is already available.
- No commercial LLM service is used at any point in the anonymization flow.

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
`requirements.txt` is the tested environment for this skill.

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
- local rewriting is constrained to avoid invented names, numbers, and locations
- low-quality generated text falls back to a deterministic local template
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
- if Ollama is reachable, preflight reports that the local server is available
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

Before the representative example, verify that the Ollama server is reachable and that the
requested model is available locally. If Ollama is unavailable, skip this example and use the
smoke test plus code inspection as the local validation path.

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

Expected result:

- the output prints a deterministic pre-embedding scrub
- the output prints expanded removal targets
- the output prints preserved public keywords
- the output prints residual DP release units
- the output prints a DP accountant with scope restricted to residual ambiguous content only
- if generation quality collapses, the final output is replaced by a deterministic template fallback

### Step 4: confirm Layer 1 behavior

Look for a preprocessing stage that:

- expands category requests like `all names` and `age`
- applies local typed replacements such as:
  - `[PERSON]`
  - `[AGE]`
  - `[ORG]`
  - `[LOCATION]`
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
- introduce new locations
- have very low semantic overlap with the scrubbed source

Expected result:

- degraded inversion text is not accepted silently

### Step 8: confirm deterministic fallback behavior

Check that when generation quality collapses, the pipeline emits a structured fallback built from:

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

If the repository later includes a `tests/` directory, the preferred regression command is:

```bash
source .venv/bin/activate
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

At minimum, the artifact should be validated against:

- category-level pre-scrub expansion
- privacy chunk limiting
- rewrite hallucination rejection
- deterministic fallback activation

Expected result:

- the CLI loads locally without import errors
- the pinned dependency environment is consistent with the artifact
- if tests are present, they pass locally

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
