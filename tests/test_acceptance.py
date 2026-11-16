"""Fast-MVP acceptance scenario (spec §18), run against the real app + Mem0 + Graphiti(Kuzu) in-process."""
import pytest
from memory_mesh_sdk import MeshAPIError

U = "user_123"


@pytest.fixture(scope="module")
def agents(owner, mk):
    a = owner.admin.create_agent("Agent A (advisor)", id="agent_a")
    b = owner.admin.create_agent("Agent B (analyst)", id="agent_b")
    owner.admin.grant(U, "agent_a", ["events:write", "memory:write", "memory:read"])
    gb = owner.admin.grant(U, "agent_b", ["memory:read", "context:read", "human:read", "semantic:read",
                                          "semantic:write", "mind:read"], source_agents=["agent_a"])
    return mk(a["api_key"]), mk(b["api_key"]), gb


def test_acceptance_flow(owner, agents):
    A, B, _ = agents
    # 1. user tells Agent A a preference -> stored as memory + human observation (+ provenance)
    r = A.events.ingest(U, "I prefer business advice that contains new information, precise evidence, "
                           "and actionable decisions.")
    assert r["memories"], r
    prefs = [o for o in r["observations"] if o["kind"] == "preference"]
    assert prefs, r["observations"]

    # 2. Agent B (different agent) retrieves the authorized memory
    hits = B.memory.search(U, "what kind of business advice does the user want?")
    assert any("actionable decisions" in h["memory"] for h in hits)
    ctx = B.context.build(U, "Make this analysis more sophisticated.")
    assert any(i["type"] == "memory" and "actionable" in i["text"] for i in ctx["items"]), ctx
    assert any(t["id"] == "sem:sophisticated" and t["decision"] == "noted" for t in ctx["trace"])

    # 3. Semantic Arena: two contrasting interpretations of 'sophisticated'
    det = B.semantic.detect("Make this analysis more sophisticated.")
    assert det["ambiguous"][0]["term"] == "sophisticated"
    cmp = B.semantic.compare(U, "sophisticated", candidates=["insight", "register"], context="business writing")
    assert len(cmp["candidates"]) == 2 and cmp["candidates"][0]["text"] != cmp["candidates"][1]["text"]

    # 4. user chooses; choice persisted and profile updated
    fb = B.semantic.feedback(U, cmp["id"], "insight")
    assert fb["weight_delta"]["novelty"] > 0 and fb["weight_delta"]["vocabulary"] < 0
    assert fb["profile"]["preferred"]["id"] == "insight"
    assert fb["observation"]["statement"].startswith("For 'sophisticated'")

    # 5. next response context uses the feedback
    ctx2 = B.context.build(U, "Make this analysis more sophisticated.", context="business writing")
    sem = [i for i in ctx2["items"] if i["type"] == "semantic"]
    assert sem and "Deeper insight" in sem[0]["text"] and cmp["id"] in sem[0]["evidence"]
    assert "Deeper insight" in ctx2["prompt"]

    # 6. provenance visible to the owner/dashboard
    mem = owner.memory.list(U)
    assert mem[0]["metadata"]["mesh_source_agent"] == "agent_a"
    assert mem[0]["metadata"]["mesh_provenance"]["type"] == "event"
    hm = owner.human.get(U)
    assert any(e["type"] == "comparison" for o in hm["dimensions"]["preference"] for e in o["evidence"])


def test_permissions_enforced(owner, agents, mk):
    A, B, gb = agents
    with pytest.raises(MeshAPIError) as e:
        B.memory.add(U, "B cannot write")  # no memory:write scope
    assert e.value.status == 403
    with pytest.raises(MeshAPIError):
        A.human.get(U)  # A has no human:read
    with pytest.raises(MeshAPIError):
        B.memory.search("someone_else", "anything")  # no grant for that user
    owner.admin.revoke(gb["id"])
    with pytest.raises(MeshAPIError) as e:
        B.memory.search(U, "advice")
    assert e.value.status == 403
    denied = [a for a in owner.admin.audit(U) if not a["allowed"]]
    assert denied


def test_unauthenticated(app_client):
    assert app_client.get("/v1/status").status_code == 401
