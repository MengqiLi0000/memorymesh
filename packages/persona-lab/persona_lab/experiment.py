"""Persona Vector Lab experiment runner.

    python -m persona_lab.experiment --model Qwen/Qwen2.5-0.5B-Instruct --out ../../benchmarks/persona_lab_results

Pipeline per trait:
  1. Generate greedy responses to every question under a positive and a negative system prompt,
     cache response-averaged activations for every layer.
  2. For each seed: random train/test split of questions; persona vector = mean difference on train;
     per-layer separation on HELD-OUT questions (projection pos - neg, Cohen's d).
  3. Reproducibility: cosine similarity of vectors across seeds and across two DISJOINT question halves;
     cross-trait cosine as a reference point.
  4. Best layer = argmax of mean held-out Cohen's d across seeds (layers 1..L).
  5. Steering sweep on held-out questions with a NEUTRAL system prompt, measured with the heuristic
     proxy metric from metrics.py, compared against prompt-based (system-prompt) control.
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import time
from pathlib import Path

import numpy as np
import torch

from . import __version__
from .metrics import TRAIT_METRICS, distinct2
from .steering import steer
from .traits import NEUTRAL_SYSTEM_PROMPT, TRAITS, get_trait
from .vectors import (
    build_prompt,
    collect_response_activations,
    collect_trait_activations,
    generate,
    load_model,
    pick_device,
    project,
)


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2) if len(a) > 1 and len(b) > 1 else 0.0
    return float((a.mean() - b.mean()) / pooled) if pooled > 0 else float("nan")


def cos(a: torch.Tensor, b: torch.Tensor) -> float:
    return float(torch.nn.functional.cosine_similarity(a.float(), b.float(), dim=-1))


def split(n: int, seed: int, n_train: int) -> tuple[list[int], list[int]]:
    idx = list(range(n))
    random.Random(seed).shuffle(idx)
    return sorted(idx[:n_train]), sorted(idx[n_train:])


def summarize(scores: list[float]) -> dict:
    a = np.asarray(scores, dtype=float)
    return {"mean": float(a.mean()), "std": float(a.std(ddof=1)) if len(a) > 1 else 0.0, "n": len(a)}


def run(args) -> dict:
    t0 = time.time()
    device = pick_device(args.device)
    torch.manual_seed(0)
    model, tok = load_model(args.model, device)
    n_layers = model.config.num_hidden_layers
    t_load = time.time() - t0
    results: dict = {
        "meta": {
            "package_version": __version__,
            "model": args.model,
            "device": device,
            "dtype": "float32",
            "num_hidden_layers": n_layers,
            "hidden_size": model.config.hidden_size,
            "max_new_tokens": args.max_new_tokens,
            "decoding": "greedy",
            "seeds": args.seeds,
            "n_train": args.n_train,
            "coeffs": args.coeffs,
            "torch": torch.__version__,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "model_load_seconds": round(t_load, 1),
        },
        "traits": {},
    }
    vectors_for_cross: dict[str, dict[int, torch.Tensor]] = {}
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for trait_name in args.traits:
        tt = time.time()
        trait = get_trait(trait_name)
        metric = TRAIT_METRICS[trait_name]
        print(f"[{trait_name}] generating contrastive responses ...", flush=True)
        ta = collect_trait_activations(model, tok, trait, args.max_new_tokens)
        nq = len(ta.questions)
        r: dict = {"n_questions": nq, "per_seed": {}}

        # prompt-elicited responses: does the proxy metric see the trait at all?
        r["prompted_metric_all_questions"] = {
            "positive_prompt": summarize([metric(x) for x in ta.pos_responses]),
            "negative_prompt": summarize([metric(x) for x in ta.neg_responses]),
        }

        d_by_seed, vecs = [], {}
        for seed in args.seeds:
            tr, te = split(nq, seed, args.n_train)
            v = ta.vector(tr)
            vecs[seed] = v
            pp = project(ta.pos_acts[te], v).numpy()  # [n_test, L+1]
            pn = project(ta.neg_acts[te], v).numpy()
            per_layer = []
            for l in range(n_layers + 1):
                per_layer.append({
                    "layer": l,
                    "proj_diff": float(pp[:, l].mean() - pn[:, l].mean()),
                    "cohens_d": cohens_d(pp[:, l], pn[:, l]),
                    "heldout_pairwise_acc": float((pp[:, l] > pn[:, l]).mean()),
                    "vector_norm": float(v[l].norm()),
                })
            d_by_seed.append([x["cohens_d"] for x in per_layer])
            r["per_seed"][str(seed)] = {"train_idx": tr, "test_idx": te, "per_layer": per_layer}
            torch.save(v, out_dir / f"{trait_name}_seed{seed}_response_avg_diff.pt")

        mean_d = np.nanmean(np.asarray(d_by_seed), axis=0)
        best = int(np.nanargmax(mean_d[1:]) + 1)  # exclude embedding layer 0
        mid = n_layers // 2
        r["best_layer"] = best
        r["best_layer_mean_heldout_d"] = float(mean_d[best])
        r["mean_heldout_d_by_layer"] = [float(x) for x in mean_d]

        # reproducibility
        s0, s1 = args.seeds[0], args.seeds[1]
        half_a, half_b = split(nq, 1234, nq // 2)
        va, vb = ta.vector(half_a), ta.vector(half_b)
        r["reproducibility"] = {
            "cos_seed_vectors_by_layer": [cos(vecs[s0][l], vecs[s1][l]) for l in range(n_layers + 1)],
            "cos_disjoint_halves_by_layer": [cos(va[l], vb[l]) for l in range(n_layers + 1)],
            "note": f"seed splits share questions (train size {args.n_train}/{nq}); disjoint halves share none",
        }
        r["reproducibility"]["cos_seed_vectors_at_best"] = r["reproducibility"]["cos_seed_vectors_by_layer"][best]
        r["reproducibility"]["cos_disjoint_halves_at_best"] = r["reproducibility"]["cos_disjoint_halves_by_layer"][best]
        vectors_for_cross[trait_name] = {l: vecs[s0][l] for l in range(n_layers + 1)}

        # steering sweep on held-out questions of the first seed, neutral system prompt
        _, te = split(nq, s0, args.n_train)
        v = vecs[s0]
        qs = [ta.questions[i] for i in te]
        neutral_prompts = [build_prompt(tok, NEUTRAL_SYSTEM_PROMPT, q) for q in qs]
        steer_res: dict = {"questions": qs, "layers": {}}
        for layer in sorted({best, mid}):
            rows = []
            for c in args.coeffs:
                print(f"[{trait_name}] steering layer={layer} coeff={c}", flush=True)
                with steer(model, v, layer, c):
                    outs = generate(model, tok, neutral_prompts, args.max_new_tokens)
                rows.append({
                    "coeff": c,
                    "metric": summarize([metric(o) for o in outs]),
                    "distinct2": summarize([distinct2(o) for o in outs]),
                    "samples": outs,
                })
            steer_res["layers"][str(layer)] = rows
        # monitoring: unsteered neutral responses projected onto the vector, vs prompted pos/neg
        neutral_out = next(rw for rw in steer_res["layers"][str(best)] if rw["coeff"] == 0)["samples"]
        neutral_acts = collect_response_activations(model, tok, neutral_prompts, neutral_out)
        steer_res["monitoring_projection_at_best_layer"] = {
            "positive_prompt": summarize(project(ta.pos_acts[te], v, best).tolist()),
            "neutral_prompt": summarize(project(neutral_acts, v, best).tolist()),
            "negative_prompt": summarize(project(ta.neg_acts[te], v, best).tolist()),
        }
        steer_res["prompting_baseline_heldout"] = {
            "positive_prompt": summarize([metric(ta.pos_responses[i]) for i in te]),
            "negative_prompt": summarize([metric(ta.neg_responses[i]) for i in te]),
            "neutral_prompt": summarize([metric(o) for o in neutral_out]),
        }
        r["steering"] = steer_res
        r["contrastive_samples"] = [
            {"question": q, "positive": p, "negative": n}
            for q, p, n in zip(ta.questions, ta.pos_responses, ta.neg_responses)
        ]
        r["seconds"] = round(time.time() - tt, 1)
        results["traits"][trait_name] = r

    names = list(vectors_for_cross)
    if len(names) >= 2:
        a, b = names[0], names[1]
        results["cross_trait_cos_by_layer"] = {
            f"{a}_vs_{b}": [cos(vectors_for_cross[a][l], vectors_for_cross[b][l]) for l in range(n_layers + 1)]
        }
    results["meta"]["total_seconds"] = round(time.time() - t0, 1)
    return results


def write_report(res: dict, path: Path) -> None:
    m = res["meta"]
    L = m["num_hidden_layers"]
    lines = [
        "# Persona Vector Lab results",
        "",
        f"Model `{m['model']}` on `{m['device']}` ({m['dtype']}, greedy, max_new_tokens={m['max_new_tokens']}). "
        f"Seeds {m['seeds']}, {m['n_train']} train questions per split. Total runtime {m['total_seconds']} s.",
        "",
        "All metrics are heuristic lexical proxies (see `packages/persona-lab/persona_lab/metrics.py`), "
        "not human or LLM-judge ratings. Sample sizes are tiny (5 held-out questions); treat as a smoke test, not evidence.",
        "",
    ]
    cross = res.get("cross_trait_cos_by_layer", {})
    cross_vals = next(iter(cross.values()), None)
    for name, r in res["traits"].items():
        b = r["best_layer"]
        rep = r["reproducibility"]
        lines += [f"## {name}", ""]
        pm = r["prompted_metric_all_questions"]
        lines += [
            f"- Proxy metric on prompt-elicited responses (all {r['n_questions']} questions): "
            f"positive prompt {pm['positive_prompt']['mean']:.2f} ± {pm['positive_prompt']['std']:.2f}, "
            f"negative prompt {pm['negative_prompt']['mean']:.2f} ± {pm['negative_prompt']['std']:.2f}",
            f"- Best layer (max mean held-out Cohen's d over seeds, layers 1..{L}): **{b}** (d = {r['best_layer_mean_heldout_d']:.2f})",
            f"- Reproducibility at layer {b}: cos(seed vectors) = {rep['cos_seed_vectors_at_best']:.3f}, "
            f"cos(disjoint question halves) = {rep['cos_disjoint_halves_at_best']:.3f}"
            + (f"; cross-trait cos at same layer = {cross_vals[b]:.3f}" if cross_vals else ""),
            "",
            "Held-out separation per layer (seed-wise: projection difference pos−neg / Cohen's d / pairwise acc):",
            "",
            "| layer | " + " | ".join(f"seed {s}" for s in r["per_seed"]) + " | cos seeds | cos halves |",
            "|---|" + "---|" * len(r["per_seed"]) + "---|---|",
        ]
        for l in range(1, L + 1):
            cells = []
            for s, ps in r["per_seed"].items():
                x = ps["per_layer"][l]
                cells.append(f"{x['proj_diff']:.2f} / {x['cohens_d']:.2f} / {x['heldout_pairwise_acc']:.2f}")
            lines.append(
                f"| {l}{' *' if l == b else ''} | " + " | ".join(cells)
                + f" | {rep['cos_seed_vectors_by_layer'][l]:.3f} | {rep['cos_disjoint_halves_by_layer'][l]:.3f} |"
            )
        st = r["steering"]
        mon = st["monitoring_projection_at_best_layer"]
        pb = st["prompting_baseline_heldout"]
        lines += [
            "",
            f"Monitoring (projection at layer {b}, held-out): positive prompt {mon['positive_prompt']['mean']:.2f}, "
            f"neutral {mon['neutral_prompt']['mean']:.2f}, negative prompt {mon['negative_prompt']['mean']:.2f}",
            "",
            f"Prompting baseline on held-out questions (proxy metric): positive {pb['positive_prompt']['mean']:.2f}, "
            f"neutral {pb['neutral_prompt']['mean']:.2f}, negative {pb['negative_prompt']['mean']:.2f}",
            "",
            "Steering sweep (neutral system prompt, held-out questions):",
            "",
            "| layer | coeff | proxy metric mean ± std | distinct-2 (coherence proxy) |",
            "|---|---|---|---|",
        ]
        for layer, rows in st["layers"].items():
            for row in rows:
                lines.append(
                    f"| {layer} | {row['coeff']:+g} | {row['metric']['mean']:.2f} ± {row['metric']['std']:.2f} "
                    f"| {row['distinct2']['mean']:.2f} |"
                )
        # one example
        lines += ["", f"Example (question: _{st['questions'][0]}_, layer {b}):", ""]
        for row in st["layers"][str(b)]:
            s = row["samples"][0].replace("\n", " ")
            lines.append(f"- coeff {row['coeff']:+g}: {s[:240]}{'…' if len(s) > 240 else ''}")
        lines.append("")
    path.write_text("\n".join(lines))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Persona Vector Lab experiment runner")
    ap.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    ap.add_argument("--traits", nargs="+", default=list(TRAITS))
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1])
    ap.add_argument("--n-train", type=int, default=7)
    ap.add_argument("--coeffs", nargs="+", type=float, default=[-8, -4, -2, 0, 2, 4, 8])
    ap.add_argument("--max-new-tokens", type=int, default=64)
    ap.add_argument("--device", default=None)
    ap.add_argument("--out", default="../../benchmarks/persona_lab_results")
    args = ap.parse_args(argv)
    if len(args.seeds) < 2:
        ap.error("need at least 2 seeds for the reproducibility check")
    res = run(args)
    out = Path(args.out)
    (out / "results.json").write_text(json.dumps(res, indent=2))
    write_report(res, out / "REPORT.md")
    print(f"wrote {out / 'results.json'} and {out / 'REPORT.md'} in {res['meta']['total_seconds']} s")


if __name__ == "__main__":
    main()
