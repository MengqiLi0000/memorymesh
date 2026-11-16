"""Computational Theory of Mind: uncertain, evidence-grounded hypotheses about a user's mental states.
Outputs are hypotheses for an assistant to use, never assertions about the person's true thoughts."""
from .errors import MeshError
from .semantic.dimensions import DIM_KEYS, extract
from .semantic import model as pm

DISCLAIMER = "Hypotheses generated from stored evidence; may be wrong. The user can correct them."


class Mind:
    def __init__(self, human, semantic, memory, llm):
        self.human, self.sem, self.mem, self.llm = human, semantic, memory, llm

    def estimate_knowledge(self, user_id: str, topic: str) -> dict:
        obs = [o for o in self.human.relevant(user_id, topic, 10, kinds=["knowledge", "fact"]) if o["relevance"] > .45]
        if not obs:
            return {"topic": topic, "estimate": "unknown", "score": None, "uncertainty": "high", "evidence": [],
                    "disclaimer": DISCLAIMER}
        num = sum(o["polarity"] * o["confidence"] * o["relevance"] for o in obs)
        den = sum(o["relevance"] for o in obs)
        sc = num / den
        lvl = "familiar" if sc > .35 else "novice" if sc < -.2 else "mixed"
        inferred_only = all(o["epistemic"] == "inferred" for o in obs)
        return {"topic": topic, "estimate": lvl, "score": round(sc, 3),
                "uncertainty": "high" if inferred_only or len(obs) < 2 else "medium",
                "evidence": [{"id": o["id"], "statement": o["statement"], "epistemic": o["epistemic"],
                              "confidence": o["confidence"]} for o in obs], "disclaimer": DISCLAIMER}

    def infer_intent(self, user_id: str, text: str, context: str = "*") -> dict:
        det = self.sem.detect(text)
        terms = []
        for a in det["ambiguous"]:
            terms.append({"term": a["term"], **(self.sem.preferred_instruction(user_id, a["term"], context)
                                               or {"status": "unknown"})})
        goals = self.human.relevant(user_id, text, 5, kinds=["goal", "intention"])
        standards = self.human.relevant(user_id, text, 6, kinds=["preference", "standard"])
        hyps = []
        for t in terms:
            if t.get("instruction"):
                hyps.append({"objective": f"By '{t['term']}', likely means: {t['label']} — {t['instruction']}",
                             "confidence": t.get("confidence"), "basis": "semantic profile",
                             "evidence": t.get("evidence", [])})
        for g in goals[:2]:
            if g["relevance"] > .4:
                hyps.append({"objective": f"Serves stated goal: {g['statement']}", "confidence": round(g['relevance'] * g['confidence'], 3),
                             "basis": "human model goal", "evidence": [g["id"]]})
        for s in standards[:3]:
            if s["relevance"] > .35:
                hyps.append({"objective": f"Output should satisfy: {s['statement']}",
                             "confidence": round(s["relevance"] * s["confidence"], 3), "basis": "stated preference",
                             "evidence": [s["id"]]})
        out = {"literal_request": text, "ambiguous_terms": terms, "hypotheses": hyps, "engine": "retrieval",
               "open_questions": [f"Which reading of '{t['term']}' is intended?" for t in terms
                                  if t.get("status") in ("unknown", None) or (t.get("confidence") or 0) < .6],
               "disclaimer": DISCLAIMER}
        if self.llm.enabled:
            ctx = "\n".join(f"- {h['objective']}" for h in hyps)
            r = self.llm.json("Given a user's literal request and evidence about them, list 2-4 plausible underlying "
                              "objectives as hypotheses with confidence in [0,1]. Do not claim certainty. "
                              'Return {"hypotheses":[{"objective","confidence","rationale"}]}',
                              f"Request: {text}\nEvidence:\n{ctx or '(none)'}")
            out["llm_hypotheses"], out["engine"] = r.get("hypotheses", []), self.llm.engine
        return out

    def evaluate(self, user_id: str, candidates: list[str], task: str = "", concept: str | None = None,
                 context: str = "*") -> dict:
        """Score candidate outputs against the user's learned criteria (semantic weights) and stated standards."""
        if not candidates:
            raise MeshError("candidates required")
        concepts = [concept] if concept else [a["term"] for a in self.sem.detect(task)["ambiguous"]] or ["*"]
        res = []
        for i, c in enumerate(candidates):
            f = extract(c)
            x = [f[k] for k in DIM_KEYS]
            per = {}
            for cn in concepts:
                lv = self.sem._levels(user_id, cn, context) if cn != "*" else self.sem._levels(user_id, "*", "*")[:1]
                per[cn] = round(pm.utility(lv, x), 4)
            score = sum(per.values()) / len(per)
            res.append({"index": i, "score": round(score, 4), "by_concept": per, "features": f})
        ranked = sorted(res, key=lambda r: -r["score"])
        std = self.human.relevant(user_id, task or " ".join(candidates)[:500], 5, kinds=["preference", "standard"])
        return {"ranking": [r["index"] for r in ranked], "candidates": res, "criteria_concepts": concepts,
                "stated_standards": [{"id": s["id"], "statement": s["statement"]} for s in std],
                "feature_engine": "lexical-proxy", "disclaimer": DISCLAIMER}

    def counterfactual(self, user_id: str, choice: str, new_information: str) -> dict:
        self.llm.require("Counterfactual preference reasoning")
        obs = self.human.relevant(user_id, choice + " " + new_information, 8)
        ctx = "\n".join(f"[{o['id']}] {o['statement']}" for o in obs)
        r = self.llm.json("EXPERIMENTAL. Estimate whether a user's choice might change given new information, "
                          "using only the evidence. This is a hypothesis, not a claim about their thoughts. "
                          'Return {"might_change": "likely|unlikely|uncertain", "confidence": 0-1, "rationale", '
                          '"evidence_ids":[]}', f"Evidence:\n{ctx}\nChoice: {choice}\nNew info: {new_information}")
        return {**r, "experimental": True, "engine": self.llm.engine, "disclaimer": DISCLAIMER}
