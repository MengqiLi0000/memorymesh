"""Write the live OpenAPI schema to apps/website/data/openapi.json (used by the REST API docs page)."""
import json, sys
from pathlib import Path
from memory_mesh.api import create_app

out = Path(__file__).resolve().parents[1] / "apps/website/data/openapi.json"
out.write_text(json.dumps(create_app().openapi(), indent=1))
print("wrote", out, file=sys.stderr)
