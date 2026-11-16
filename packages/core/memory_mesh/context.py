"""Context Engine: compiles the most useful authorized context for a task under a token budget.
Deterministic: fixed scoring weights, stable tie-breaks, token estimate = ceil(chars/4)."""
import math

TYPE_WEIGHT = {"semantic": 1.0, "standard": 0.95, "preference": 0.9, "memory": 0.8, "graph": 0.75,
               "goal": 0.7, "knowledge": 0.6, "other_obs": 0.5}


def tokens(s: str) -> int:
    return math.ceil(len(s) / 4)


class ContextEngine:
    def __init__(self, memory, graph, human, semantic):
        self.memory, self.graph, self.human, self.sem = memory, graph, human, semantic

    async def build(self, user_id: str, task: str, budget: int = 800, context: str = "*",
                    mem_sources=None, allow: dict | None = None) -> dict:
        allow = allow or {}
        items, trace = [], []
        if allow.get("semantic", True):
            for a in self.sem.detect(task)["ambiguous"]:
                p = self.sem.preferred_instruction(user_id, a["term"], context)
                if p:
                    items.append({"type": "semantic", "id": f"sem:{p['concept']}",
                                  "text": f"When the user says '{a['surface']}', they have preferred: {p['label']} — "
                                          f"{p['instruction']} (confidence {p['confidence']}, {p['status']})",
                                  "relevance": 1.0, "confidence": p["confidence"] or .5,
                                  "evidence": p["evidence"]})
                else:
                    trace.append({"id": f"sem:{a['term']}", "decision": "noted",
                                  "reason": "ambiguous term with no learned preference", "uncertain": True})
        if allow.get("memory", True):
            for m in self.memory.search(task, user_id, mem_sources, top_k=10):
                items.append({"type": "memory", "id": m["id"], "text": m["memory"], "relevance": m.get("score", 0),
                              "confidence": 1.0, "source_agent": (m.get("metadata") or {}).get("mesh_source_agent"),
                              "evidence": [m["id"]]})
        if allow.get("human", True):
            for o in self.human.relevant(user_id, task, 10):
                t = o["kind"] if o["kind"] in TYPE_WEIGHT else ("other_obs")
                items.append({"type": t, "id": o["id"], "text": o["statement"], "relevance": o["relevance"],
                              "confidence": o["confidence"], "epistemic": o["epistemic"],
                              "evidence": [e.get("id") for e in o["evidence"]]})
        if allow.get("graph", True) and self.graph.enabled:
            try:
                for e in await self.graph.search(user_id, task, 6):
                    items.append({"type": "graph", "id": e["uuid"], "text": e["fact"] + (
                        f" (no longer valid since {e['invalid_at']})" if e["invalid_at"] else ""),
                                  "relevance": 0.6, "confidence": 0.5 if e["invalid_at"] else 1.0,
                                  "valid_at": e["valid_at"], "invalid_at": e["invalid_at"], "evidence": [e["uuid"]]})
            except Exception as ex:
                trace.append({"id": "graph", "decision": "skipped", "reason": f"graph error: {ex}"})
        for it in items:
            it["score"] = round(TYPE_WEIGHT.get(it["type"], .5) * (0.5 + 0.5 * float(it["relevance"] or 0))
                                * (0.5 + 0.5 * float(it["confidence"] or 0)), 4)
            it["tokens"] = tokens(it["text"])
        items.sort(key=lambda i: (-i["score"], i["id"]))
        chosen, used, seen = [], 0, set()
        for it in items:
            key = it["text"].lower().strip()
            if key in seen:
                trace.append({"id": it["id"], "decision": "excluded", "reason": "duplicate text", "score": it["score"]})
                continue
            if it["score"] < 0.3:
                trace.append({"id": it["id"], "decision": "excluded", "reason": "score below 0.3", "score": it["score"]})
                continue
            if used + it["tokens"] > budget:
                trace.append({"id": it["id"], "decision": "excluded", "reason": "token budget", "score": it["score"]})
                continue
            seen.add(key)
            used += it["tokens"]
            chosen.append(it)
            trace.append({"id": it["id"], "decision": "included", "score": it["score"], "tokens": it["tokens"]})
        uncertain = [c["id"] for c in chosen if c.get("epistemic") == "inferred" or (c.get("confidence") or 1) < .6]
        lines = ["## What is known about this user (authorized context)"]
        for c in chosen:
            tag = " [inferred]" if c.get("epistemic") == "inferred" else ""
            lines.append(f"- ({c['type']}){tag} {c['text']}")
        if uncertain:
            lines.append("Items marked [inferred] or low-confidence are hypotheses; ask if they matter.")
        return {"user_id": user_id, "task": task, "budget": budget, "used_tokens": used, "items": chosen,
                "trace": trace, "uncertain": uncertain, "prompt": "\n".join(lines) if chosen else ""}
