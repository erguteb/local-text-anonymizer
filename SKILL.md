# Claw4S Submission: Local Anonymizer Improvement

## Skill Summary

This skill upgrades a local text anonymization pipeline into a three-layer privacy architecture:

1. Deterministic local scrubbing for explicit sensitive information.
2. Deterministic preservation of approved public or utility-preserving slots.
3. Differentially private protection and accounting for ambiguous residual information only.

The skill is intended for codebases that already contain a local anonymizer and need to be hardened so that:
- no commercial LLM services are used,
- explicit sensitive spans are scrubbed before embedding or generation,
- only ambiguous residual content is inside the DP mechanism,
- low-quality generated outputs fall back to deterministic local rendering.

## Inputs

- `REPO_PATH`: path to the anonymizer repository
- `ENTRY_FILE`: main CLI or pipeline file to patch and run
- `TEST_PATH`: test directory or target test files
- `LOCAL_LLM_BACKEND`: one of `ollama` or `hf`

## Default Artifact Instance

For the reference artifact used during development of this skill:

- `REPO_PATH=/home/ubuntu/vec2text-with-inclusion-of-keyword`
- `ENTRY_FILE=main.py`
- `TEST_PATH=tests`
- `LOCAL_LLM_BACKEND=ollama`

If the artifact is hosted publicly, also provide:

- `REPO_URL`: public Git repository URL
- `REPO_COMMIT`: pinned commit hash to check out before execution

## Preconditions

- The repository is available locally.
- Python 3 is installed.
- The anonymizer already runs locally or can be patched to do so.
- If `LOCAL_LLM_BACKEND=ollama`, a local Ollama server is running and the target model is pulled.

If the repository is not already present locally but is publicly hosted, acquire it with a pinned revision before continuing:

```bash
git clone "$REPO_URL" "$REPO_PATH"
cd "$REPO_PATH"
git checkout "$REPO_COMMIT"
```

Do not rely on an unpinned branch name for review-time execution.

## Step 1: Inspect the current pipeline

### Goal

Find where the repository currently handles:
- explicit removals,
- keyword or slot preservation,
- embedding perturbation,
- privacy accounting,
- local regeneration,
- final output rendering.

### Commands

```bash
cd "$REPO_PATH"
rg -n "remove|keyword|sigma|delta|epsilon|paraphrase|ollama|hf|baseline|sentence|chunk" "$ENTRY_FILE"
sed -n '1,260p' "$ENTRY_FILE"
python3 "$ENTRY_FILE" --help
```

### Expected output

- Locations of the scrub, keyword, DP, and rewrite logic are identified.
- The main entrypoint and current CLI flags are visible.

## Step 2: Classify the current design into the three layers

### Goal

Map the existing implementation to:
- Layer 1: explicit sensitive information
- Layer 2: approved public or utility-preserving information
- Layer 3: ambiguous residual information

### Actions

- Record whether explicit removals happen before or after embeddings.
- Record whether approved public slots are currently perturbed.
- Record whether DP accounting is currently scoped to the full text or only the residual content.

### Expected output

- A short written classification of the current architecture.
- A list of architectural failures to patch.

## Step 3: Patch Layer 1 so deterministic scrub happens before embeddings

### Goal

Ensure explicit sensitive spans are locally scrubbed before any embedding or local generation step.

### Required implementation

- Add typed expansion for category-level removals such as:
  - `all names`
  - `age`
  - `all employers`
  - `all locations`
- Replace fragile literal-only removal with typed local scrubbing rules.
- Use placeholders such as:
  - `[PERSON]`
  - `[AGE]`
  - `[ORG]`
  - `[LOCATION]`

### Commands

```bash
cd "$REPO_PATH"
rg -n "parse_removal|replace_targets|literal" "$ENTRY_FILE"
```

### Expected output

- The pipeline has a deterministic preprocessing function that returns scrubbed text before the DP path.
- Category-level removals are expanded locally without calling any commercial service.

## Step 4: Patch Layer 2 so approved public slots are preserved outside DP

### Goal

Treat user-approved public or utility-preserving content as deterministic slots, not private residual content.

### Required implementation

- Preserve approved keywords or slots separately from the residual text.
- Keep them outside the DP accountant.
- Reuse them later during final rendering.

### Commands

```bash
cd "$REPO_PATH"
rg -n "keywords|public|slot|preserve" "$ENTRY_FILE"
```

### Expected output

- Approved public keywords remain available after preprocessing.
- The code explicitly treats them as outside the DP mechanism.

## Step 5: Patch Layer 3 so only ambiguous residual content enters the DP mechanism

### Goal

Restrict DP perturbation and accounting to the ambiguous residual content only.

### Required implementation

- Build residual text after Layer 1 scrub and Layer 2 slot extraction.
- Segment residual text conservatively.
- Add a CLI parameter to cap release count, such as `--max-privacy-chunks`.
- Compute DP accounting using:
  - `num_releases`
  - `sigma`
  - `delta`
  - `sensitivity`
  - composed `epsilon`

### Commands

```bash
cd "$REPO_PATH"
rg -n "epsilon|delta|sigma|sensitivity|num_releases|chunk" "$ENTRY_FILE"
```

### Expected output

- The accountant explicitly states that its scope is residual ambiguous content only.
- Release count is bounded by a chunk cap instead of naive sentence explosion.

## Step 6: Constrain local regeneration

### Goal

Keep local rewriting from inventing facts when inversion quality degrades.

### Required implementation

- Allow only local backends.
- Tighten local prompts so they:
  - preserve placeholders,
  - do not add names,
  - do not add numbers,
  - do not add new locations,
  - simplify degraded text instead of hallucinating.
- Add rejector checks for:
  - novel capitalized entities,
  - novel numbers,
  - low lexical overlap,
  - obvious collapse patterns.

### Commands

```bash
cd "$REPO_PATH"
rg -n "paraphrase|rewrite|ollama|fallback|collapse|halluc" "$ENTRY_FILE"
```

### Expected output

- Local rewrite is constrained.
- Bad local generations are rejected instead of accepted.

## Step 7: Add deterministic template fallback

### Goal

Produce a usable final output even when inversion or local rewriting quality is poor.

### Required implementation

- Build a deterministic renderer from:
  - scrubbed local text,
  - approved public slots,
  - simple fixed labels such as `Context`, `Request`, `Task`, `Location`, `Preferences`
- Trigger the fallback when the generated output collapses.

### Expected output

- The final output is always usable and locally generated.
- The fallback does not invent facts.

## Step 8: Make the CLI and output state the privacy scope clearly

### Goal

Expose the three layers directly in the runtime output.

### Required implementation

The CLI output should print:
- deterministic pre-embedding scrub,
- expanded removal targets,
- preserved public keywords,
- residual DP release units,
- DP accountant scope,
- final output source, either generated or deterministic fallback.

### Expected output

- A reviewer can tell exactly what was scrubbed, what was preserved, and what was covered by DP.

## Step 9: Add regression tests

### Goal

Validate the three-layer behavior locally.

### Required test cases

- typed category removal such as `all names` and `age`
- public keyword preservation
- DP release count limiting
- hallucination rejection
- deterministic fallback activation

### Commands

```bash
cd "$REPO_PATH"
python3 -m unittest discover -s "$TEST_PATH" -p 'test_*.py' -v
```

### Expected output

- Tests pass locally.
- The three-layer behavior is covered by automated checks.

## Step 10: Produce a final audit summary

### Goal

Summarize whether the repository now satisfies the intended privacy architecture.

### Required summary fields

- `local_only`: `yes` or `no`
- `layer1_deterministic_scrub_before_embedding`: `yes` or `no`
- `layer2_public_slots_outside_dp`: `yes` or `no`
- `layer3_residual_only_dp_scope`: `yes` or `no`
- `dp_accounting_reported`: `yes` or `no`
- `deterministic_fallback_present`: `yes` or `no`
- `remaining_limitations`: short list

### Expected output

- A concise machine-readable or bullet summary of the final state.

## Acceptance Criteria

The skill succeeds only if all of the following are true:

- The anonymization process is fully local.
- Explicit sensitive information is scrubbed before embeddings.
- Approved public or utility-preserving slots are kept outside the DP mechanism.
- DP accounting is reported only for ambiguous residual content.
- Low-quality generated outputs are replaced by deterministic local fallback rendering.
- Automated tests pass locally.

## Notes for Claw Review

- This skill is designed to be executed end-to-end on an existing anonymizer repository.
- It is generalizable to other local privacy-preserving text preprocessing pipelines.
- It prioritizes auditability over fluent but unverifiable rewriting.
