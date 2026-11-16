"""Simulated-user benchmark for Semantic Arena preference learning (synthetic; NOT human data).

Each simulated user has hidden dimension weights = shared user taste + concept-specific offset.
Choices are sampled from a Bradley-Terry model. We train on N comparisons and measure held-out
choice-prediction accuracy for: chance, population-majority, concept-only model, hierarchical model,
plus TRANSFER: accuracy on a concept the model never saw comparisons for."""
import json, math, random, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages/core"))
from memory_mesh.semantic import model as pm
from memory_mesh.semantic.lexicon import SEED
from memory_mesh.semantic.dimensions import DIM_KEYS

CONCEPTS = ["sophisticated", "professional", "insightful", "improve", "value", "quality", "depth", "optimize"]


def sim_user(rng, taste_sd=1.0, concept_sd=0.4):
    g = [rng.gauss(0, taste_sd) for _ in DIM_KEYS]
    return {c: [gi + rng.gauss(0, concept_sd) for gi in g] for c in CONCEPTS}


def sample_pair(rng, c):
    a, b = rng.sample(SEED[c], 2)
    return a, b, pm.vec(a["dims"]), pm.vec(b["dims"])


def choose(rng, w, xa, xb, temp=1.0):
    u = sum(wi * (a - b) for wi, a, b in zip(w, xa, xb)) / temp
    return rng.random() < 1 / (1 + math.exp(-u))


def run(n_users=200, n_train=12, n_test=30, seed=0):
    rng = random.Random(seed)
    acc = {"oracle_ceiling": 0, "chance": 0, "majority": 0, "concept_only": 0, "hierarchical": 0,
           "transfer_hierarchical": 0, "transfer_chance": 0}
    tot, tot_t = 0, 0
    # population majority: per (concept, pair) which interpretation wins more often across training users
    pop = {}
    users = [sim_user(rng) for _ in range(n_users)]
    for u in users[: n_users // 2]:
        for _ in range(n_train):
            c = rng.choice(CONCEPTS); a, b, xa, xb = sample_pair(rng, c)
            k = (c, *sorted([a["id"], b["id"]]))
            win = a["id"] if choose(rng, u[c], xa, xb) else b["id"]
            pop.setdefault(k, {}).setdefault(win, 0); pop[k][win] += 1
    for u in users[n_users // 2:]:
        held = rng.choice(CONCEPTS)
        train_c = [c for c in CONCEPTS if c != held]
        lv_h, lv_c = {}, {}
        for _ in range(n_train):
            c = rng.choice(train_c); a, b, xa, xb = sample_pair(rng, c)
            wa = choose(rng, u[c], xa, xb)
            w, l = (xa, xb) if wa else (xb, xa)
            pm.update([lv_h.setdefault("*", pm.blank("user")), lv_h.setdefault(c, pm.blank("concept"))], w, l)
            pm.update([lv_c.setdefault(c, pm.blank("concept"))], w, l)
        for _ in range(n_test):
            c = rng.choice(train_c); a, b, xa, xb = sample_pair(rng, c)
            truth = choose(rng, u[c], xa, xb)
            tot += 1
            acc["chance"] += rng.random() < .5
            acc["oracle_ceiling"] += (sum(wi * (p - q) for wi, p, q in zip(u[c], xa, xb)) > 0) == truth
            k = (c, *sorted([a["id"], b["id"]])); votes = pop.get(k, {})
            maj = votes.get(a["id"], 0) >= votes.get(b["id"], 0)
            acc["majority"] += maj == truth
            acc["concept_only"] += (pm.predict([lv_c.get(c, pm.blank("concept"))], xa, xb)[0] > .5) == truth
            acc["hierarchical"] += (pm.predict([lv_h.get("*", pm.blank("user")), lv_h.get(c, pm.blank("concept"))],
                                               xa, xb)[0] > .5) == truth
            a, b, xa, xb = sample_pair(rng, held)
            truth = choose(rng, u[held], xa, xb)
            tot_t += 1
            acc["transfer_chance"] += rng.random() < .5
            acc["transfer_hierarchical"] += (pm.predict([lv_h.get("*", pm.blank("user")), pm.blank("concept")],
                                                        xa, xb)[0] > .5) == truth
    res = {k: round(v / (tot_t if k.startswith("transfer") else tot), 4) for k, v in acc.items()}
    return {"config": dict(n_users=n_users, n_train=n_train, n_test=n_test, seed=seed), "accuracy": res}


if __name__ == "__main__":
    out = [run(seed=s, n_train=n) for s in (0, 1, 2) for n in (4, 12, 30)]
    Path(__file__).with_name("results").mkdir(exist_ok=True)
    Path(__file__).with_name("results").joinpath("semantic_sim.json").write_text(json.dumps(out, indent=1))
    print(f"{'seed':>4} {'n_train':>7} " + " ".join(f"{k:>21}" for k in out[0]["accuracy"]))
    for r in out:
        print(f"{r['config']['seed']:>4} {r['config']['n_train']:>7} " + " ".join(f"{v:>21}" for v in r["accuracy"].values()))
