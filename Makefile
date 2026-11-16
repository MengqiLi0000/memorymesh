.PHONY: install serve test bench demo
install:
	uv sync --all-packages
serve:
	uv run memory-mesh serve
test:
	uv run pytest -q
bench:
	uv run python benchmarks/semantic_sim.py && uv run python benchmarks/memory_retrieval.py
demo:
	MESH_ADMIN_KEY=$$(uv run memory-mesh admin-key) uv run python examples/two_agents.py
