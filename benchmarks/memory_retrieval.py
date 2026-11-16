"""Memory retrieval + cross-agent correctness + latency on a small synthetic dataset, against the real
Mem0-backed module (offline: fastembed bge-small, raw storage). Synthetic data; not a standard benchmark."""
import json, os, statistics, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages/core"))
os.environ["MESH_DATA_DIR"] = tempfile.mkdtemp()
os.environ["MESH_LLM_PROVIDER"] = "none"
from memory_mesh.config import Settings
from memory_mesh.memory import MemoryModule

FACTS = [
    ("I am allergic to peanuts", "what food allergies do I have?"),
    ("My daughter Mia starts school in September", "when does my kid start school?"),
    ("I prefer Python over JavaScript for data work", "which language for data analysis?"),
    ("Our company's fiscal year ends in March", "when does the fiscal year close?"),
    ("I run 10k every Sunday morning", "what is my weekend exercise routine?"),
    ("My manager is called Lena Ortiz", "who is my boss?"),
    ("I'm vegetarian since 2019", "do I eat meat?"),
    ("The board meeting moved to Thursday", "when is the board meeting?"),
    ("I want reports under two pages", "how long should my reports be?"),
    ("I live in Lisbon near the river", "which city do I live in?"),
    ("My cofounder Priya handles fundraising", "who manages investor relations?"),
    ("I use a standing desk and dislike long calls", "what are my meeting preferences?"),
]

m = MemoryModule(Settings().ensure())
ids = {}
for i, (f, _) in enumerate(FACTS):
    agent = "agent_a" if i % 2 == 0 else "agent_b"
    ids[f] = m.add(f, "bench_user", agent, infer=False)["results"][0]["id"]
m.add("Unrelated user fact: I am allergic to cats", "other_user", "agent_a", infer=False)

hits1, hits3, lat, leak, xagent_ok = 0, 0, [], 0, 0
for f, q in FACTS:
    t = time.perf_counter(); res = m.search(q, "bench_user", None, top_k=3); lat.append((time.perf_counter() - t) * 1000)
    got = [r["memory"] for r in res]
    hits1 += got[:1] == [f]; hits3 += f in got
    leak += any("cats" in g for g in got)
    restricted = m.search(q, "bench_user", {"agent_a"}, top_k=12)
    xagent_ok += all((r["metadata"]["mesh_source_agent"] == "agent_a") for r in restricted)
out = {"n": len(FACTS), "recall@1": round(hits1 / len(FACTS), 3), "recall@3": round(hits3 / len(FACTS), 3),
       "cross_user_leaks": leak, "source_agent_filter_correct": f"{xagent_ok}/{len(FACTS)}",
       "search_latency_ms": {"median": round(statistics.median(lat), 1), "max": round(max(lat), 1)},
       "embedder": "BAAI/bge-small-en-v1.5 (fastembed)", "llm": "none"}
Path(__file__).with_name("results").mkdir(exist_ok=True)
Path(__file__).with_name("results").joinpath("memory_retrieval.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
