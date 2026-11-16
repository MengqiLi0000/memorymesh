#!/usr/bin/env bash
# Register the Memory Mesh MCP server with Claude Code.
# Usage: MESH_API_KEY=<agent key> MESH_USER_ID=<user> ./add.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
claude mcp add memory-mesh \
  -e MESH_URL="${MESH_URL:-http://127.0.0.1:8765}" \
  -e MESH_API_KEY="${MESH_API_KEY:?set MESH_API_KEY}" \
  -e MESH_USER_ID="${MESH_USER_ID:?set MESH_USER_ID}" \
  -- uv run --directory "$REPO" memory-mesh-mcp
