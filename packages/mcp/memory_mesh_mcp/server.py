"""Memory Mesh MCP server (stdio). Uses the official `mcp` SDK (MCPServer) for transport and the Memory Mesh
Python SDK for calls, so every tool call goes through the API's permission checks with this agent's key.

Env: MESH_URL, MESH_API_KEY (an agent key), MESH_USER_ID (default user for tools)."""
import json, os
from mcp.server.mcpserver import MCPServer
from memory_mesh_sdk import MemoryMesh

mcp = MCPServer("memory-mesh")
_mesh = None


def mesh() -> MemoryMesh:
    global _mesh
    _mesh = _mesh or MemoryMesh()
    return _mesh


def _u(user_id: str | None) -> str:
    u = user_id or os.getenv("MESH_USER_ID")
    if not u:
        raise ValueError("user_id required (or set MESH_USER_ID)")
    return u


def _j(x) -> str:
    return json.dumps(x, indent=1, default=str)


@mcp.tool()
def remember(content: str, user_id: str | None = None, kind: str = "message") -> str:
    """Store something the user said or an authorized observation about them (memory + human model + graph)."""
    return _j(mesh().events.ingest(_u(user_id), content, kind=kind))


@mcp.tool()
def search_memory(query: str, user_id: str | None = None, top_k: int = 8) -> str:
    """Search the user's authorized memories."""
    return _j(mesh().memory.search(_u(user_id), query, top_k=top_k))


@mcp.tool()
def build_context(task: str, user_id: str | None = None, budget: int = 800) -> str:
    """Compile the most useful authorized personal context for a task, with a trace of what was selected and why."""
    r = mesh().context.build(_u(user_id), task, budget)
    return r["prompt"] + "\n\n<trace>\n" + _j(r["trace"]) + "\n</trace>"


@mcp.tool()
def query_user_model(question: str, user_id: str | None = None) -> str:
    """Ask what is known about the user (evidence-linked; distinguishes observed vs inferred)."""
    return _j(mesh().human.query(_u(user_id), question))


@mcp.tool()
def interpret_term(term: str, user_id: str | None = None, context: str = "*") -> str:
    """How has this user interpreted an ambiguous word like 'sophisticated' or 'professional'?"""
    return _j(mesh().semantic.interpret(_u(user_id), term, context))


@mcp.tool()
def start_comparison(concept: str, user_id: str | None = None, candidates: list[str] | None = None,
                     context: str = "*") -> str:
    """Create an A/B comparison of interpretations (or candidate texts) to learn what the user means."""
    return _j(mesh().semantic.compare(_u(user_id), concept, candidates, context))


@mcp.tool()
def record_choice(comparison_id: str, selected: str, user_id: str | None = None) -> str:
    """Record which candidate the user chose in a comparison."""
    return _j(mesh().semantic.feedback(_u(user_id), comparison_id, selected))


@mcp.tool()
def infer_intent(text: str, user_id: str | None = None) -> str:
    """Compare the literal request with plausible underlying objectives (hypotheses with evidence)."""
    return _j(mesh().mind.infer_intent(_u(user_id), text))


def main():
    mcp.run()


if __name__ == "__main__":
    main()
