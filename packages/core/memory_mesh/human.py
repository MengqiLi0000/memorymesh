"""Human Model: evidence-grounded, versioned observations about a user.
Independent implementation (no Honcho code) of the general derive -> consolidate -> query pattern.
Every row is 'observed' (user said it) or 'inferred' (hypothesis) with confidence and evidence."""
import math, re
from .errors import NotFound, MeshError
from .store import Store, new_id, now

KINDS = ["fact", "preference", "knowledge", "belief", "goal", "intention", "standard", "relationship"]
STOP = set("i me my the a an to of and or for in on at with that this it is are be was am do does about more "
           "less very really just so than into from by as you your we our they".split())

# (kind, regex, polarity, epistemic, confidence)
PATTERNS = [
    ("preference", r"\bi (?:really |strongly )?(?:prefer|like|love|value|appreciate|enjoy)\b (?P<x>[^.!?\n]+)", 1, "observed", .85),
    ("preference", r"\bi (?:don't|do not|dislike|hate|can't stand|cannot stand)\b (?:like |want )?(?P<x>[^.!?\n]+)", -1, "observed", .85),
    ("standard", r"\b(?:please )?(?:always|never) (?P<x>[^.!?\n]+)", 1, "observed", .8),
    ("standard", r"\b(?:good|great) (?:\w+ ){0,3}(?:should|must|needs to) (?P<x>[^.!?\n]+)", 1, "observed", .75),
    ("standard", r"\b(?:too|overly) (?P<x>long|verbose|generic|vague|formal|casual|wordy|shallow|technical|simple)\b", -1, "observed", .7),
    ("goal", r"\b(?:i(?:'m| am) (?:trying|planning|aiming|hoping) to|my goal is to|i want to|i need to) (?P<x>[^.!?\n]+)", 1, "observed", .8),
    ("intention", r"\bi(?:'m| am)? (?:going to|gonna|will) (?P<x>[^.!?\n]+)", 1, "observed", .7),
    ("belief", r"\bi (?:think|believe|suspect|feel) (?:that )?(?P<x>[^.!?\n]+)", 1, "observed", .7),
    ("knowledge", r"\bi (?:know|understand|am familiar with|have (?:worked|experience) (?:with|in)) (?P<x>[^.!?\n]+)", 1, "observed", .75),
    ("knowledge", r"\b(?:i(?:'m| am) new to|i don't (?:know|understand)|i(?:'m| am) not familiar with) (?P<x>[^.!?\n]+)", -1, "observed", .75),
    ("fact", r"\bi (?:work|live) (?:at|in|for) (?P<x>[^.!?\n,]+)", 1, "observed", .9),
    ("fact", r"\bi(?:'m| am) (?:a|an|the) (?P<x>[a-z ]{3,40}?)(?: at| in| for|[.,!?]|$)", 1, "observed", .85),
    ("relationship", r"\bmy (?P<x>(?:wife|husband|partner|boss|manager|cofounder|co-founder|colleague|friend|mother|father|"
                     r"son|daughter|sister|brother|team|investor|client)\b[^.!?\n,]{0,40})", 1, "observed", .8),
]
ROLE_EXPERTISE = {  # cautious inferred hypotheses from stated roles
    "cfo": "finance and accounting", "cto": "software engineering", "founder": "starting and running a company",
    "engineer": "engineering", "doctor": "medicine", "lawyer": "law", "investor": "investing",
    "product manager": "product management", "designer": "design", "analyst": "analysis", "consultant": "consulting",
    "teacher": "teaching", "researcher": "research", "data scientist": "data science", "economist": "economics",
}
NEG = re.compile(r"\b(not|no|never|don't|doesn't|dislike|hate|stop|avoid|without|less)\b", re.I)


def keywords(text: str, k=4):
    ws = [w for w in re.findall(r"[a-z][a-z-]+", text.lower()) if w not in STOP and len(w) > 2]
    return ws[:k]


def cos(a, b):
    if not a or not b:
        return 0.0
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb or 1)


class HumanModel:
    def __init__(self, store: Store, llm, embed_fn):
        self.db, self.llm, self.embed = store, llm, embed_fn

    # ---------- derivation
    def derive(self, user_id: str, text: str, evidence: dict, source_agent: str | None = None,
               context: str = "") -> list[dict]:
        cands = self._derive_llm(text) if self.llm.enabled else self._derive_heuristic(text)
        out = []
        for c in cands:
            c["evidence"] = [{**evidence, "quote": c.pop("quote", text[:300])}]
            out.append(self._consolidate(user_id, c, source_agent, context))
        return out

    def _derive_heuristic(self, text: str) -> list[dict]:
        res = []
        for sent in re.split(r"(?<=[.!?])\s+|\n", text):
            s = sent.strip()
            for kind, pat, pol, epi, conf in PATTERNS:
                for m in re.finditer(pat, s, re.I):
                    x = m.group("x").strip(" ,;:")
                    if len(x) < 3:
                        continue
                    stmt = {"preference": ("Prefers " if pol > 0 else "Dislikes ") + x,
                            "standard": ("Expects outputs to: " + x) if pol > 0 else f"Has objected to output being too {x}",
                            "goal": "Goal: " + x, "intention": "Intends to " + x, "belief": "Believes " + x,
                            "knowledge": ("Knows about " if pol > 0 else "Is new to ") + x,
                            "fact": "Stated: " + s.rstrip(".!?"), "relationship": "Mentioned their " + x}[kind]
                    res.append({"kind": kind, "statement": stmt, "polarity": pol, "epistemic": epi,
                                "confidence": conf, "topic": " ".join(keywords(x)), "quote": s})
                    if kind == "fact":
                        for role, area in ROLE_EXPERTISE.items():
                            if re.search(rf"\b{role}\b", x, re.I):
                                res.append({"kind": "knowledge", "statement": f"Likely has working knowledge of {area} "
                                            f"(inferred from stated role '{role}')", "polarity": 1,
                                            "epistemic": "inferred", "confidence": .5, "topic": area, "quote": s})
        return res

    def _derive_llm(self, text: str) -> list[dict]:
        r = self.llm.json(
            "You extract an evidence-grounded model of a USER from their message. Only include claims supported by "
            f"the text. kinds: {KINDS}. epistemic='observed' if the user stated it directly, 'inferred' if it is "
            "your hypothesis. Never infer psychological or clinical traits. confidence in [0,1]; inferred <= 0.6. "
            'Return {"observations":[{"kind","statement","topic","polarity"(1|-1),"epistemic","confidence","quote"}]}',
            text)
        out = []
        for o in r.get("observations", []):
            if o.get("kind") in KINDS and o.get("statement"):
                o["confidence"] = min(float(o.get("confidence", .5)), .6 if o.get("epistemic") == "inferred" else 1)
                out.append(o)
        return out

    # ---------- consolidation
    def _consolidate(self, user_id: str, c: dict, source_agent, context) -> dict:
        emb = self.embed(c["statement"])
        pol = int(c.get("polarity", 1))
        best, best_sim = None, 0.0
        for o in self.db.query("SELECT * FROM observations WHERE user_id=? AND kind=? AND status='active'",
                               [user_id, c["kind"]]):
            s = cos(emb, o["embedding"])
            if s > best_sim:
                best, best_sim = o, s
        ts = now()
        if best and best_sim >= 0.90 and best["polarity"] == pol:
            conf = min(0.97, 1 - (1 - best["confidence"]) * (1 - c["confidence"]))
            ev = best["evidence"] + c["evidence"]
            self._version(best, "merged duplicate observation")
            self.db.exec("UPDATE observations SET confidence=?, evidence=?, updated_at=? WHERE id=?",
                         [conf, ev, ts, best["id"]])
            return {**self.get(best["id"]), "consolidation": "merged", "similarity": round(best_sim, 3)}
        row = {"id": new_id("obs"), "user_id": user_id, "kind": c["kind"], "epistemic": c.get("epistemic", "observed"),
               "statement": c["statement"], "topic": c.get("topic", ""), "context": context,
               "confidence": float(c["confidence"]), "polarity": pol, "evidence": c["evidence"], "status": "active",
               "user_verdict": None, "superseded_by": None, "source_agent": source_agent,
               "engine": self.llm.engine, "embedding": emb, "created_at": ts, "updated_at": ts}
        self.db.insert("observations", row)
        self._version(row, "created")
        note = "created"
        contradicts = best and best_sim >= 0.75 and (best["polarity"] != pol or
                                                     bool(NEG.search(best["statement"])) != bool(NEG.search(c["statement"])))
        if contradicts:
            self._version(best, f"superseded by newer contradicting observation {row['id']}")
            self.db.exec("UPDATE observations SET status='superseded', superseded_by=?, updated_at=? WHERE id=?",
                         [row["id"], ts, best["id"]])
            note = "superseded_previous"
        out = self.get(row["id"])
        out["consolidation"] = note
        if contradicts:
            out["supersedes"] = best["id"]
        return out

    def _version(self, o: dict, reason: str):
        n = self.db.one("SELECT COUNT(*) c FROM observation_versions WHERE observation_id=?", [o["id"]])["c"]
        snap = {k: v for k, v in o.items() if k != "embedding"}
        self.db.insert("observation_versions", {"observation_id": o["id"], "version": n + 1, "snapshot": snap,
                                                "reason": reason, "ts": now()})

    # ---------- read
    @staticmethod
    def _public(o):
        o = dict(o)
        o.pop("embedding", None)
        return o

    def get(self, oid: str) -> dict:
        o = self.db.one("SELECT * FROM observations WHERE id=?", [oid])
        if not o:
            raise NotFound(f"observation {oid} not found")
        return self._public(o)

    def model(self, user_id: str, include_inactive=False) -> dict:
        q = "SELECT * FROM observations WHERE user_id=?" + ("" if include_inactive else " AND status='active'")
        obs = [self._public(o) for o in self.db.query(q + " ORDER BY updated_at DESC", [user_id])]
        by = {k: [o for o in obs if o["kind"] == k] for k in KINDS}
        return {"user_id": user_id, "dimensions": by,
                "summary": {"observed": sum(o["epistemic"] == "observed" for o in obs),
                            "inferred": sum(o["epistemic"] == "inferred" for o in obs),
                            "low_confidence": sum(o["confidence"] < .6 for o in obs)},
                "disclaimer": "Observations are evidence-linked hypotheses, not assessments of the person."}

    def history(self, oid: str):
        return self.db.query("SELECT * FROM observation_versions WHERE observation_id=? ORDER BY version", [oid])

    def relevant(self, user_id: str, query: str, k=8, kinds=None) -> list[dict]:
        qe = self.embed(query)
        rows = self.db.query("SELECT * FROM observations WHERE user_id=? AND status='active' "
                             "AND COALESCE(user_verdict,'') != 'rejected'", [user_id])
        if kinds:
            rows = [r for r in rows if r["kind"] in kinds]
        for r in rows:
            r["relevance"] = round(cos(qe, r["embedding"]), 4)
        rows.sort(key=lambda r: -r["relevance"])
        return [self._public(r) for r in rows[:k]]

    def query(self, user_id: str, question: str, k=8) -> dict:
        obs = self.relevant(user_id, question, k)
        uncertain = [o for o in obs if o["epistemic"] == "inferred" or o["confidence"] < .6]
        ans, engine = None, "retrieval-only"
        if self.llm.enabled and obs:
            ctx = "\n".join(f"[{o['id']}] ({o['kind']}, {o['epistemic']}, conf {o['confidence']:.2f}) {o['statement']}"
                            for o in obs)
            ans = self.llm.text("Answer a question about a user ONLY from the observations given. Cite ids in "
                                "brackets. Separate what was observed from what is inferred. Say what is uncertain.",
                                f"Observations:\n{ctx}\n\nQuestion: {question}")
            engine = self.llm.engine
        return {"question": question, "answer": ans, "engine": engine, "observations": obs,
                "uncertain": [o["id"] for o in uncertain],
                "note": None if obs else "No relevant evidence; the system does not know."}

    # ---------- correction
    def correct(self, user_id: str, oid: str, action: str, statement: str | None = None) -> dict:
        o = self.db.one("SELECT * FROM observations WHERE id=? AND user_id=?", [oid, user_id])
        if not o:
            raise NotFound(f"observation {oid} not found")
        self._version(o, f"user {action}")
        ts = now()
        if action == "confirm":
            self.db.exec("UPDATE observations SET user_verdict='confirmed', epistemic='observed', confidence=0.99, "
                         "updated_at=? WHERE id=?", [ts, oid])
        elif action == "reject":
            self.db.exec("UPDATE observations SET user_verdict='rejected', status='rejected', updated_at=? WHERE id=?",
                         [ts, oid])
        elif action == "correct":
            if not statement:
                raise MeshError("statement required for correct")
            self.db.exec("UPDATE observations SET statement=?, embedding=?, user_verdict='corrected', "
                         "epistemic='observed', confidence=0.99, updated_at=? WHERE id=?",
                         [statement, self.embed(statement), ts, oid])
        elif action == "delete":
            self.db.exec("DELETE FROM observations WHERE id=?", [oid])
            self.db.exec("DELETE FROM observation_versions WHERE observation_id=?", [oid])
            return {"id": oid, "deleted": True}
        else:
            raise MeshError("action must be confirm|reject|correct|delete")
        return self.get(oid)

    def add_observation(self, user_id, kind, statement, epistemic="observed", confidence=.9, polarity=1,
                        evidence=None, source_agent=None, context=""):
        if kind not in KINDS:
            raise MeshError(f"kind must be one of {KINDS}")
        return self._consolidate(user_id, {"kind": kind, "statement": statement, "epistemic": epistemic,
                                           "confidence": confidence, "polarity": polarity,
                                           "evidence": evidence or [{"type": "manual"}],
                                           "topic": " ".join(keywords(statement))}, source_agent, context)

    def revoke_evidence(self, user_id: str, source_type: str, source_id: str):
        """Deletion propagation: drop evidence pointing at a deleted source; delete observations left with none."""
        for o in self.db.query("SELECT * FROM observations WHERE user_id=?", [user_id]):
            ev = [e for e in o["evidence"] if not (e.get("type") == source_type and e.get("id") == source_id)]
            if len(ev) != len(o["evidence"]):
                if ev:
                    self.db.exec("UPDATE observations SET evidence=? WHERE id=?", [ev, o["id"]])
                else:
                    self.db.exec("DELETE FROM observations WHERE id=?", [o["id"]])

    def export(self, user_id):
        return [{**self._public(o), "versions": self.history(o["id"])}
                for o in self.db.query("SELECT * FROM observations WHERE user_id=?", [user_id])]
