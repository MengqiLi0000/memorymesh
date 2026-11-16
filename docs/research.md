# Research notes: established methods vs Memory Mesh hypotheses

## Established methods used
- **Bradley–Terry paired-comparison model** (Bradley & Terry, 1952): P(a ≻ b) = σ(u(a) − u(b)).
- **Linear reward over features / personalized reward modeling**: utility u(x) = w·x, as in preference-based RL and RLHF reward models (Christiano et al., 2017).
- **Online Bayesian logistic regression with a diagonal Gaussian posterior** (Laplace / assumed-density updates; Spiegelhalter & Lauritzen, 1990), with the probit approximation for the predictive (MacKay, 1992).
- **Hierarchical (partially pooled) models**: user-level + concept-level + context-level weights.
- **Active learning by uncertainty sampling** (Lewis & Gale, 1994): query the pair whose predicted outcome is closest to 0.5.
- **Persona vectors** (Chen et al., 2025, arXiv:2507.21509; Anthropic research post "Persona vectors"): mean-difference activation directions from contrastive system prompts, used for monitoring and steering.
- Related areas for further reading: pragmatic interpretation (Rational Speech Acts; Goodman & Frank, 2016), contextual semantics, ToM evaluation of LLMs (e.g., Kosinski 2023 and its critiques; Ullman 2023).

## Memory Mesh hypotheses (not established; under test)
1. **Shared quality dimensions enable semantic transfer**: a user's choices about "professional" predict their reading of "sophisticated" because both map onto shared dimensions (evidence, novelty, formality, ...).
   *Evidence so far*: on simulated users only (benchmarks/semantic_sim.py), transfer accuracy is above chance. No human-subject data yet.
2. **Operational interpretations beat vague terms in prompts**: replacing "make it more sophisticated" with the user's learned operational reading improves user-rated output. *Not yet tested* (needs LLM + human raters).
3. **Model-behavior vectors could implement user preferences** (persona-lab Track 3). *Not tested*; must be compared against prompt-based personalization.

## Known limitations
- The offline text feature extractor (`semantic/dimensions.py`) is a transparent lexical proxy, not a validated measure.
- Heuristic human-model derivation is English-only, pattern-based, and conservative; LLM mode is needed for real coverage.
- Simulated-user benchmarks validate the learning machinery, not real human behavior.
