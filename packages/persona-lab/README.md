# Persona Vector Lab (`memory-mesh-persona-lab`)

**Status: experimental, optional.** Nothing in Memory Mesh core depends on this package.

A small, self-contained lab for *persona vectors* on small open-weight language models: extract a
direction in a model's residual stream that corresponds to a character trait, use it to **monitor**
(project activations onto it) and to **steer** (add it to the residual stream during generation).

It reimplements, at toy scale, the method of

> Chen et al. *Persona Vectors: Monitoring and Controlling
> Character Traits in Language Models.* 2025. arXiv:2507.21509.

Note on the citation: the upstream repository README (commit b8e0f04) does not state the arXiv id; the id
above was given to us and was not independently verified from inside the repo.

## Scientific scope: model behavior is not user preference

Please read this before connecting anything here to Memory Mesh memory.

- A **persona vector** describes how *the model* behaves (e.g. how formal or how sycophantic its
  outputs are). It is a property of model activations under a given prompt distribution.
- A **user preference representation** describes what *a user* wants (e.g. "prefers short, formal
  answers"). In Memory Mesh, user preferences are **Track 2** and live in the core **Semantic Arena**
  as explicit, inspectable, editable memory. That is the supported path.
- These are **not equivalent**. A steering vector that makes a model more formal is not evidence that
  a user prefers formality, and a stored preference does not imply that a vector exists which faithfully
  realizes it without side effects (coherence loss, collateral trait shifts).
- **Track 3** (using stored preferences to select/scale behavior vectors at inference time) is
  **planned/experimental only**. Any Track 3 result must be compared against the obvious baseline:
  **prompt-based personalization** (putting the preference into the system prompt). The experiment
  runner already reports this baseline next to every steering result. In our tiny run below, small
  steering coefficients moved the lexical proxy *further* than the system-prompt baseline, but larger
  coefficients quickly broke coherence. Prompting never did. Neither result says anything about whether
  this matches what a user actually prefers.

## Closed models

Persona vectors require access to internal activations. This package works only with open-weight
models loaded locally through `transformers`. It has **no access to, and makes no claims about,
closed/API models** (Claude, GPT, Gemini, ...). For those, prompt-based personalization is the only option.

## What's in the package

| module | contents |
|---|---|
| `persona_lab/traits.py` | Trait definitions: `formality`, `sycophancy`. Each has 2 positive + 2 negative system prompts and 12 evaluation questions (all original text). |
| `persona_lab/vectors.py` | `load_model`, `collect_trait_activations`, `extract_vectors(model_name, trait) -> Tensor[layers+1, hidden]`, `mean_difference`, `project`. Adapted from upstream `generate_vec.py`. |
| `persona_lab/steering.py` | `steer(model, vector, layer, coeff)` context manager (forward hook). Adapted from upstream `activation_steer.py`. |
| `persona_lab/metrics.py` | Transparent heuristic proxy metrics (lexical formality score, agree/correct keyword score, distinct-2 repetition proxy). |
| `persona_lab/experiment.py` | Experiment runner CLI (`persona-lab` / `python -m persona_lab`). |
| `tests/test_core.py` | Offline tests on tiny random-init Qwen2 / GPT-2 configs (no download). |

### Method (as implemented)

1. For each question, generate a greedy response under a positive system prompt and under a negative
   system prompt (chat template, `max_new_tokens=64`).
2. Run the model over `prompt + response` and average the hidden states over **response tokens**
   for every layer (`hidden_states[0]` = embeddings, `hidden_states[l]` = output of block `l-1`).
   This is upstream's `response_avg_diff` variant (the one used in the paper).
3. Persona vector per layer = mean(positive) − mean(negative) over the training questions.
4. Monitoring: scalar projection of response activations onto the unit-normalised vector.
5. Steering: add `coeff * v[l]` (raw, un-normalised, as upstream) to the output of block `l-1` at all
   positions during generation.

Differences from upstream: no LLM-judge filtering of the contrastive responses (we keep all pairs),
no LLM-judge evaluation, much smaller question sets, and 2 traits we wrote ourselves.

### Experiment runner

Per trait: random train/test split of questions (default 7/5) for each seed; per-layer **held-out**
separation (projection difference, Cohen's d, pairwise accuracy pos>neg); best layer = argmax of
mean held-out d across seeds; reproducibility = cosine similarity between seed vectors and between
vectors from two **disjoint** question halves (plus cross-trait cosine as a reference); steering sweep
(default coeffs −8, −4, −2, 0, 2, 4, 8) at the best layer and at the middle layer on held-out questions
with a neutral system prompt, scored with the proxy metric, next to the prompting baseline.

## How to run

```bash
cd packages/persona-lab
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e '.[test]'

.venv/bin/python -m pytest -q                       # offline, ~2 s
.venv/bin/python -m persona_lab.experiment \
    --model Qwen/Qwen2.5-0.5B-Instruct \
    --out ../../benchmarks/persona_lab_results       # downloads ~1 GB on first run
```

Options: `--traits`, `--seeds`, `--n-train`, `--coeffs`, `--max-new-tokens`, `--device {mps,cpu,cuda}`.
Outputs: `results.json` (all numbers + every generated sample), `REPORT.md`, and the per-seed vectors
(`<trait>_seed<k>_response_avg_diff.pt`, shape `[layers+1, hidden]`).

Python API:

```python
from persona_lab import load_model, extract_vectors, steer, project
model, tok = load_model("Qwen/Qwen2.5-0.5B-Instruct")
v = extract_vectors("Qwen/Qwen2.5-0.5B-Instruct", "formality", model=model, tokenizer=tok)  # [25, 896]
with steer(model, v, layer=12, coeff=4.0):
    ...  # model.generate(...)
```

## Results

Real run: `Qwen/Qwen2.5-0.5B-Instruct` (24 layers, hidden 896), Apple Silicon `mps`, float32, greedy,
64 new tokens, seeds 0/1, 7 train / 5 held-out questions. **End-to-end runtime 106 s** (wall clock 107 s,
including model load). Full numbers and every generated sample are in
`benchmarks/persona_lab_results/results.json` and `REPORT.md`. All trait scores come from the heuristic proxies.

**Held-out separation and reproducibility**

| trait | best layer (by held-out d) | mean held-out Cohen's d | held-out pairwise acc | cos(seed 0, seed 1 vectors) | cos(disjoint halves) | cross-trait cos (same layer) |
|---|---|---|---|---|---|---|
| formality | 20 | 2.81 | 1.00 (both seeds) | 0.947 | 0.879 | −0.274 |
| sycophancy | 16 | 1.77 | 1.00 (both seeds) | 0.835 | 0.481 | −0.196 |

The formality vector is stable across question splits. The sycophancy vector is much less stable: it
gets 0.48 across disjoint halves of only 6 questions each. Separation is high at nearly every layer,
which is expected given the system-prompt confound (see Limitations).

**Monitoring** (projection at the best layer, held-out questions; ordering positive > neutral > negative):
formality 6.25 / 3.88 / −3.41; sycophancy 0.66 / −0.57 / −0.92.

**Steering** (neutral system prompt, 5 held-out questions; proxy mean; distinct-2 is a coherence proxy, where values near 1 mean no repetition):

| trait | layer | −8 | −4 | −2 | 0 | +2 | +4 | +8 | prompting baseline (neg / neutral / pos) |
|---|---|---|---|---|---|---|---|---|---|
| formality | 12 | −11.1 (0.98) | −12.7 (1.00) | −7.9 (0.99) | 1.4 (0.97) | 7.1 (0.97) | 8.4 (0.99) | 9.1 (0.91) | −2.65 / 1.36 / 2.82 |
| formality | 20 | −112.3 (0.03) | −72.8 (0.20) | −16.3 (0.96) | 1.4 (0.97) | 11.2 (0.98) | 25.8 (0.76) | −22.5 (0.00) | |
| sycophancy | 12 | 0.00 (0.68) | −0.42 (0.93) | −0.65 (0.96) | −0.20 (0.96) | 0.66 (1.00) | 0.33 (1.00) | 0.00 (0.97) | −0.08 / −0.20 / 0.57 |
| sycophancy | 16 | −0.79 (0.45) | −0.67 (0.80) | −0.60 (0.95) | −0.20 (0.96) | 0.35 (0.98) | 0.61 (0.99) | 0.50 (0.89) | |

What we observed:
- At |coeff| ≤ 2, steering changed the proxy in the expected direction for both traits and at both
  layers, and coherence stayed intact. Layer 12 was usable up to ±8 for formality.
- At the best-separation layer (20) for formality, |coeff| ≥ 4 broke the output: "like ya ya ya …" at −8,
  and drift into repeated Chinese tokens at +4/+8. The proxy scores −112 and −22.5 come from this
  degenerate text and **do not show a trait effect**. The layer that separates best is not
  necessarily the best layer to steer.
- For sycophancy at layer 16, coeffs −2 and −4 turned "That's correct!" (unsteered, wrong) into
  "No, that is incorrect." Coeffs +2 and +4 gave "Absolutely! You're absolutely right!". The model's
  facts stayed unreliable under every setting, so steering changed the tone, not the accuracy.
- The unsteered 0.5B model was already somewhat sycophantic on these false-premise prompts.


## Limitations

- **Tiny scale**: 12 questions per trait, 5 held-out questions, one 0.5B model, greedy decoding.
  Numbers are a smoke test of the pipeline, not scientific evidence.
- **Proxy metrics**: formality and sycophancy are scored by keyword/lexical heuristics
  (`metrics.py`). They are transparent but crude, can be gamed by surface wording, and were not
  validated against human ratings. Distinct-2 is only a weak degeneration signal.
- **Confound in separation**: positive/negative activations are collected with different system
  prompts in context, so held-out separation partly reflects the instruction text, not only the
  response style. High Cohen's d is therefore expected and is a weak test; steering is the stronger test.
- **No judge filtering**: upstream keeps only pairs where a judge confirms the trait was expressed; we keep all.
- **Coefficient units**: the raw mean-difference vector is used, so `coeff` is relative to that
  layer's pos−neg difference norm and not comparable across layers or models.
- Steering is unstable at high coefficients and late layers (see results): gibberish can hit the
  keyword lists, so always read the distinct-2 column and the samples.
- Reproducibility checks use overlapping (seed) and disjoint (halves) question sets from the same
  small pool; they say nothing about other prompt distributions.

## Attribution

`persona_lab/vectors.py` and `persona_lab/steering.py` are adapted from
[safety-research/persona_vectors](https://github.com/safety-research/persona_vectors)
(Apache-2.0), commit `b8e0f044fe2410a6fad579f38324f03f13b4e917`, modified by Memory Mesh; see the
file headers and `NOTICE`. Trait prompts, questions, metrics, and the experiment runner are original.
