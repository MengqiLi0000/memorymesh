import os, secrets
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("MESH_DATA_DIR", "./data")).resolve())
    llm_provider: str = field(default_factory=lambda: os.getenv("MESH_LLM_PROVIDER", "none"))
    llm_model: str | None = field(default_factory=lambda: os.getenv("MESH_LLM_MODEL"))
    llm_api_key: str | None = field(default_factory=lambda: os.getenv("MESH_LLM_API_KEY"))
    embed_model: str = field(default_factory=lambda: os.getenv("MESH_EMBED_MODEL", "BAAI/bge-small-en-v1.5"))
    embed_dims: int = field(default_factory=lambda: int(os.getenv("MESH_EMBED_DIMS", "384")))
    graph_backend: str = field(default_factory=lambda: os.getenv("MESH_GRAPH", "kuzu"))  # kuzu | neo4j | falkordb | off
    neo4j_uri: str | None = field(default_factory=lambda: os.getenv("NEO4J_URI"))
    neo4j_user: str | None = field(default_factory=lambda: os.getenv("NEO4J_USER"))
    neo4j_password: str | None = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD"))
    falkordb_host: str = field(default_factory=lambda: os.getenv("FALKORDB_HOST", "localhost"))
    admin_key: str | None = field(default_factory=lambda: os.getenv("MESH_ADMIN_KEY"))
    cors_origins: list[str] = field(default_factory=lambda: os.getenv(
        "MESH_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","))

    def ensure(self) -> "Settings":
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.admin_key:
            kf = self.data_dir / "admin.key"
            if not kf.exists():
                kf.write_text(secrets.token_urlsafe(24))
                kf.chmod(0o600)
            self.admin_key = kf.read_text().strip()
        os.environ.setdefault("MEM0_TELEMETRY", "False")
        os.environ.setdefault("GRAPHITI_TELEMETRY_ENABLED", "false")
        return self

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider not in ("", "none", None)
