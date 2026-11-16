import pytest
from memory_mesh_sdk import MeshAPIError

U = "user_mod"


def test_memory_crud_history_export(owner):
    r = owner.memory.add(U, "I live in Lisbon and work at Northwind")
    mid = r["results"][0]["id"]
    assert owner.memory.get(U, mid)["memory"].startswith("I live in Lisbon")
    owner.memory.update(U, mid, "I live in Porto and work at Northwind")
    hist = owner.memory.history(U, mid)
    assert [h["event"] for h in hist][:2] == ["ADD", "UPDATE"]
    exp = owner.admin.export(U)
    assert exp["memories"][0]["history"]
    owner.memory.delete(U, mid)
    with pytest.raises(MeshAPIError):
        owner.memory.get(U, mid)


def test_graph_temporal(owner):
    owner.graph.add_fact(U, "Dana", "works_at", "Acme", "Dana works at Acme", valid_at="2024-01-01T00:00:00Z",
                         invalid_at="2025-06-01T00:00:00Z")
    owner.graph.add_fact(U, "Dana", "works_at", "Globex", "Dana works at Globex", valid_at="2025-06-01T00:00:00Z")
    now = {e["fact"] for e in owner.graph.search(U, "where does Dana work", as_of="2026-01-01T00:00:00Z")}
    past = {e["fact"] for e in owner.graph.search(U, "where does Dana work", as_of="2024-06-01T00:00:00Z")}
    assert "Dana works at Globex" in now and "Dana works at Acme" not in now
    assert "Dana works at Acme" in past
    snap = owner.graph.snapshot(U)
    assert {n["name"] for n in snap["nodes"]} >= {"Dana", "Acme", "Globex"}


def test_event_graph_and_delete_propagation(owner):
    r = owner.events.ingest(U, "I work at Contoso. My cofounder is Priya Shah.")
    assert r["graph"]["edges"], r["graph"]
    ev = r["event_id"]
    d = owner.events.delete(U, ev)
    assert d["propagated"]["memories"] and d["propagated"]["edges"]
    assert not [o for o in owner.human.get(U)["dimensions"]["fact"] if "Contoso" in o["statement"]]


def test_human_consolidation_and_correction(owner):
    owner.human.infer(U, "I prefer short answers.")
    r = owner.human.infer(U, "I prefer short answers.")
    assert r[0]["consolidation"] == "merged" and r[0]["confidence"] > 0.85
    r2 = owner.human.infer(U, "I'm a CFO at a retail company.")
    inferred = [o for o in r2 if o["epistemic"] == "inferred"]
    assert inferred and inferred[0]["confidence"] <= 0.6
    c = owner.human.correct(U, inferred[0]["id"], "reject")
    assert c["status"] == "rejected"
    assert len(owner.human.history(U, inferred[0]["id"])) >= 2
    k = owner.mind.estimate_knowledge(U, "finance and accounting")
    assert k["estimate"] == "unknown" or all(e["id"] != inferred[0]["id"] for e in k["evidence"])


def test_contradiction_supersedes(owner):
    a = owner.human.observe(U, "preference", "Prefers long detailed reports", polarity=1)
    b = owner.human.observe(U, "preference", "Does not prefer long detailed reports", polarity=-1)
    assert b["consolidation"] == "superseded_previous" and b["supersedes"] == a["id"]


def test_semantic_transfer_and_eval(owner):
    u = "user_sem"
    for _ in range(3):
        c = owner.semantic.compare(u, "professional", ["precision", "formal"])
        owner.semantic.feedback(u, c["id"], "precision")
    it = owner.semantic.interpret(u, "sophisticated")
    assert it["status"] == "transferred" and it["preferred"]["id"] == "rigor"
    ev = owner.semantic.evaluate(u)
    assert ev["n"] == 3 and ev["accuracy"]["hierarchical"] == 1.0


def test_semantic_text_candidates_and_evaluate(owner):
    u = "user_txt"
    a = "Revenue grew 14% in Q3 (company 10-Q). Recommend cutting the two lowest-margin SKUs by Friday."
    b = "Our amazing, world-class strategy will unlock incredible synergies in today's fast-paced market!"
    c = owner.semantic.compare(u, "professional", [{"id": "a", "text": a}, {"id": "b", "text": b}])
    owner.semantic.feedback(u, c["id"], "a")
    ev = owner.mind.evaluate(u, [b, a], task="make it more professional")
    assert ev["ranking"][0] == 1


def test_consent_required(owner):
    with pytest.raises(MeshAPIError):
        owner.events.ingest(U, "transcript", kind="voice_transcript", consent={"user_authorized": True})
    r = owner.events.ingest(U, "I'm planning to launch the product in March.", kind="voice_transcript",
                            consent={"user_authorized": True, "bystanders_notified_or_absent": True})
    assert any(o["kind"] == "goal" for o in r["observations"])


def test_llm_only_features_report_unavailable(owner):
    with pytest.raises(MeshAPIError) as e:
        owner.mind.counterfactual(U, "chose vendor A", "vendor A raised prices 30%")
    assert e.value.status == 503
