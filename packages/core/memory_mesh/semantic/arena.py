"""Semantic Arena: detect ambiguous language, generate operational interpretations, run contrastive
A/B comparisons with active query selection, learn a personal semantic profile, and evaluate it."""
import itertools, re
from ..errors import NotFound, MeshError
from ..store import Store, new_id, now
from . import model
from .dimensions import DIM_KEYS, DIMENSIONS, extract
from .lexicon import ALIASES, GENERIC, SEED

DETECT_RE = re.compile(r"\b(?:more|less|too|not)\s+([a-z][a-z-]{3,})\b", re.I)


class SemanticArena:
    def __init__(self, store: Store, llm):
        self.db, self.llm = store, llm

    # ---------------- lexicon
    def _lookup(self, term: str) -> tuple[str, list[dict], str] | None:
        t = term.strip().lower()
        canon = ALIASES.get(t, t)
        if canon in SEED:
            return canon, SEED[canon], "seed"
        row = self.db.one("SELECT * FROM sem_concepts WHERE term=?", [canon])
        if row:
            return row["canonical"], row["interpretations"], row["source"]
        return None

    def concepts(self) -> list[dict]:
        out = [{"term": k, "source": "seed", "interpretations": len(v)} for k, v in SEED.items()]
        out += [{"term": r["term"], "source": r["source"], "interpretations": len(r["interpretations"])}
                for r in self.db.query("SELECT * FROM sem_concepts")]
        return out

    # ---------------- detection
    def detect(self, text: str) -> dict:
        low = text.lower()
        found, seen = [], set()
        terms = sorted(set(SEED) | set(ALIASES) | {r["term"] for r in self.db.query("SELECT term FROM sem_concepts")},
                       key=len, reverse=True)
        for t in terms:
            for m in re.finditer(r"(?<![\w])" + re.escape(t) + r"(?![\w])" if t.isascii() else re.escape(t), low):
                canon = ALIASES.get(t, t)
                if any(s <= m.start() < e for s, e in seen):
                    continue
                seen.add((m.start(), m.end()))
                found.append({"term": canon, "surface": text[m.start():m.end()], "span": [m.start(), m.end()],
                              "known": True, "confidence": 0.9})
        for m in DETECT_RE.finditer(text):
            w = m.group(1).lower()
            if not any(s <= m.start(1) < e for s, e in seen) and not self._lookup(w):
                found.append({"term": w, "surface": m.group(0), "span": [m.start(1), m.end(1)], "known": False,
                              "confidence": 0.5})
        if self.llm.enabled and not found:
            try:
                r = self.llm.json("Find evaluative or underspecified words in the user's request whose meaning "
                                  "depends on personal taste (e.g. 'sophisticated', 'better'). "
                                  'Return {"terms":[...]}', text)
                for t in r.get("terms", []):
                    i = low.find(t.lower())
                    found.append({"term": t.lower(), "surface": t, "span": [i, i + len(t)], "known": False,
                                  "confidence": 0.6, "engine": self.llm.engine})
            except Exception:
                pass
        return {"text": text, "ambiguous": sorted(found, key=lambda f: f["span"][0]), "engine": self.llm.engine}

    def _interpretations(self, term: str) -> tuple[str, list[dict], str]:
        hit = self._lookup(term)
        if hit:
            return hit
        if self.llm.enabled:
            r = self.llm.json(
                "Give 3-4 DISTINCT operational interpretations of an ambiguous quality word as used in a request "
                "to an AI. Each: id (slug), label, instruction (imperative, one sentence), dims (object mapping "
                f"a subset of these keys to weights in [-1,1]: {', '.join(DIM_KEYS)}). "
                'Return {"interpretations":[...]}', f"Word: {term}")
            ints = [i for i in r["interpretations"] if isinstance(i.get("dims"), dict)]
            ints = [{**i, "dims": {k: float(v) for k, v in i["dims"].items() if k in DIMENSIONS}} for i in ints]
            self.db.insert("sem_concepts", {"term": term.lower(), "canonical": term.lower(), "interpretations": ints,
                                            "source": self.llm.engine, "created_at": now()})
            return term.lower(), ints, self.llm.engine
        return term.lower(), GENERIC, "generic-fallback"

    # ---------------- profile
    def _levels(self, user_id: str, concept: str, context: str) -> list[dict]:
        keys = [("*", "*", "user"), (concept, "*", "concept"), (concept, context or "*", "context")]
        out = []
        for c, x, lvl in keys:
            r = self.db.one("SELECT * FROM sem_profiles WHERE user_id=? AND concept=? AND context=?", [user_id, c, x])
            L = {"mean": r["mean"], "var": r["var"], "n": r["n"]} if r else model.blank(lvl)
            L["key"] = (c, x)
            out.append(L)
        if (context or "*") == "*":
            out = out[:2]
        return out

    def _save(self, user_id, levels):
        for L in levels:
            c, x = L["key"]
            self.db.insert("sem_profiles", {"user_id": user_id, "concept": c, "context": x, "mean": L["mean"],
                                            "var": L["var"], "n": L["n"], "updated_at": now()})

    def interpret(self, user_id: str, term: str, context: str = "*") -> dict:
        concept, ints, source = self._interpretations(term)
        levels = self._levels(user_id, concept, context)
        scored = []
        for it in ints:
            x = model.vec(it["dims"])
            scored.append({**it, "score": round(model.utility(levels, x), 4)})
        scored.sort(key=lambda s: -s["score"])
        conf = None
        if len(scored) >= 2:
            p, _ = model.predict(levels, model.vec(scored[0]["dims"]), model.vec(scored[1]["dims"]))
            conf = round(p, 3)
        evidence = self.db.query("SELECT id,comparison_id,selected,context,ts FROM sem_feedback WHERE user_id=? AND "
                                 "concept=? ORDER BY ts DESC LIMIT 20", [user_id, concept])
        n_obs = sum(L["n"] for L in levels[1:])
        return {"user_id": user_id, "term": term, "concept": concept, "context": context, "source": source,
                "interpretations": scored, "preferred": scored[0] if n_obs or levels[0]["n"] else None,
                "confidence_top_vs_next": conf, "observations": {"concept": n_obs, "user_global": levels[0]["n"]},
                "status": "learned" if n_obs else ("transferred" if levels[0]["n"] else "unknown"),
                "next_query": self._select_pair(levels, scored), "evidence": evidence}

    @staticmethod
    def _select_pair(levels, cands) -> dict | None:
        """Uncertainty sampling: the pair whose outcome the model is least sure about (max entropy, tie->variance)."""
        best = None
        for a, b in itertools.combinations(cands, 2):
            p, v = model.predict(levels, model.vec(a["dims"]), model.vec(b["dims"]))
            score = (-abs(p - 0.5), v)
            if best is None or score > best[0]:
                best = (score, a["id"], b["id"], p)
        return {"a": best[1], "b": best[2], "p_a": round(best[3], 3)} if best else None

    # ---------------- comparisons
    def compare(self, user_id: str, concept: str, candidates: list | None = None, context: str = "*",
                task: str = "", agent_id: str | None = None) -> dict:
        """candidates: list of interpretation ids, or dicts {id?, text} of candidate outputs.
        If omitted, the actively selected most-informative pair of interpretations is used."""
        canon, ints, _ = self._interpretations(concept)
        levels = self._levels(user_id, canon, context)
        by_id = {i["id"]: i for i in ints}
        if not candidates:
            q = self._select_pair(levels, ints)
            candidates = [q["a"], q["b"]]
        cands = []
        for k, c in enumerate(candidates):
            if isinstance(c, str) and c in by_id:
                it = by_id[c]
                cands.append({"id": c, "kind": "interpretation", "label": it["label"], "text": it["instruction"],
                              "features": model.vec(it["dims"])})
            else:
                text = c["text"] if isinstance(c, dict) else str(c)
                cid = (c.get("id") if isinstance(c, dict) else None) or f"candidate_{chr(97 + k)}"
                feats = extract(text)
                cands.append({"id": cid, "kind": "text", "label": cid, "text": text,
                              "features": [feats[k2] for k2 in DIM_KEYS], "feature_engine": "lexical-proxy"})
        if len(cands) < 2:
            raise MeshError("need at least two candidates")
        preds = {}
        for a in cands:
            preds[a["id"]] = round(sum(model.predict(levels, a["features"], b["features"])[0]
                                       for b in cands if b is not a) / (len(cands) - 1), 4)
        row = {"id": new_id("cmp"), "user_id": user_id, "agent_id": agent_id, "concept": canon, "context": context,
               "task": task, "candidates": cands, "predicted": preds, "selected": None, "selected_at": None,
               "created_at": now()}
        self.db.insert("sem_comparisons", row)
        return {**row, "dimensions": DIM_KEYS}

    def get_comparison(self, cid: str) -> dict:
        r = self.db.one("SELECT * FROM sem_comparisons WHERE id=?", [cid])
        if not r:
            raise NotFound(f"comparison {cid} not found")
        return r

    def feedback(self, user_id: str, comparison_id: str, selected: str) -> dict:
        c = self.get_comparison(comparison_id)
        if c["user_id"] != user_id:
            raise NotFound("comparison not found for user")
        if c["selected"]:
            raise MeshError("comparison already answered", selected=c["selected"])
        win = next((x for x in c["candidates"] if x["id"] == selected), None)
        if not win:
            raise MeshError(f"'{selected}' is not a candidate", candidates=[x["id"] for x in c["candidates"]])
        levels = self._levels(user_id, c["concept"], c["context"])
        before = model.weights(levels)
        losers = [x for x in c["candidates"] if x["id"] != selected]
        ps = [model.update(levels, win["features"], l["features"]) for l in losers]
        self._save(user_id, levels)
        self.db.exec("UPDATE sem_comparisons SET selected=?, selected_at=? WHERE id=?", [selected, now(), comparison_id])
        fb = {"id": new_id("sfb"), "user_id": user_id, "comparison_id": comparison_id, "concept": c["concept"],
              "context": c["context"], "selected": selected, "rejected": [l["id"] for l in losers],
              "features": {"win": win["features"], "lose": [l["features"] for l in losers]},
              "predicted_p": round(sum(ps) / len(ps), 4), "ts": now()}
        self.db.insert("sem_feedback", fb)
        after = model.weights(levels)
        delta = {k: round(after[k] - before[k], 4) for k in after if abs(after[k] - before[k]) > 1e-4}
        return {"feedback": fb, "winner": {"id": win["id"], "label": win["label"], "text": win["text"]},
                "prediction_before_feedback": fb["predicted_p"], "weight_delta": delta,
                "profile": self.interpret(user_id, c["concept"], c["context"])}

    def profile(self, user_id: str) -> dict:
        rows = self.db.query("SELECT * FROM sem_profiles WHERE user_id=?", [user_id])
        return {"user_id": user_id, "dimensions": DIMENSIONS,
                "levels": [{"concept": r["concept"], "context": r["context"], "n": r["n"],
                            "weights": dict(zip(DIM_KEYS, [round(v, 4) for v in r["mean"]])),
                            "variance": dict(zip(DIM_KEYS, [round(v, 4) for v in r["var"]]))} for r in rows],
                "comparisons": self.db.query("SELECT id,concept,context,selected,created_at FROM sem_comparisons "
                                             "WHERE user_id=? ORDER BY created_at DESC LIMIT 50", [user_id])}

    def evaluate(self, user_id: str) -> dict:
        """Leave-one-out held-out choice prediction over this user's real feedback log, versus a 50% chance
        baseline and a non-hierarchical (concept-only) model."""
        fbs = self.db.query("SELECT * FROM sem_feedback WHERE user_id=? ORDER BY ts", [user_id])
        pairs = [(f, w, l) for f in fbs for w, l in [(f["features"]["win"], x) for x in f["features"]["lose"]]]
        if len(pairs) < 2:
            return {"user_id": user_id, "n": len(pairs), "note": "need at least 2 pairwise choices"}
        hits = {"hierarchical": 0, "concept_only": 0}
        for i, (f, w, l) in enumerate(pairs):
            for mode in hits:
                lv: dict = {}
                for j, (f2, w2, l2) in enumerate(pairs):
                    if j == i:
                        continue
                    levels = self._eval_levels(lv, f2, mode)
                    model.update(levels, w2, l2)
                levels = self._eval_levels(lv, f, mode)
                p, _ = model.predict(levels, w, l)
                hits[mode] += p > 0.5
        n = len(pairs)
        return {"user_id": user_id, "n": n, "method": "leave-one-out",
                "accuracy": {k: round(v / n, 3) for k, v in hits.items()}, "chance": 0.5}

    @staticmethod
    def _eval_levels(store: dict, f: dict, mode: str):
        keys = [("*", "*", "user"), (f["concept"], "*", "concept"), (f["concept"], f["context"], "context")]
        if mode == "concept_only":
            keys = keys[1:2]
        return [store.setdefault(k[:2], model.blank(k[2])) for k in keys]

    def preferred_instruction(self, user_id: str, term: str, context: str = "*") -> dict | None:
        r = self.interpret(user_id, term, context)
        if not r["preferred"]:
            return None
        return {"term": term, "concept": r["concept"], "instruction": r["preferred"]["instruction"],
                "label": r["preferred"]["label"], "confidence": r["confidence_top_vs_next"], "status": r["status"],
                "evidence": [e["comparison_id"] for e in r["evidence"]]}
