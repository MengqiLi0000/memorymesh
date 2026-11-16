"""SQLite persistence for Memory Mesh state that upstream libraries do not model
(identity, grants, audit, raw events, human model, semantic arena).
Why not reuse: Mem0 stores memories + history and Graphiti stores graphs; neither
has tables for consent grants, observation versions or pairwise preference logs."""
import json, sqlite3, threading, uuid
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY, name TEXT, description TEXT, key_hash TEXT UNIQUE, created_at TEXT);
CREATE TABLE IF NOT EXISTS grants(id TEXT PRIMARY KEY, user_id TEXT, agent_id TEXT, scopes TEXT, source_agents TEXT,
  note TEXT, created_at TEXT, revoked_at TEXT);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, actor TEXT, user_id TEXT, action TEXT,
  resource TEXT, allowed INTEGER, detail TEXT);
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, user_id TEXT, agent_id TEXT, kind TEXT, content TEXT, payload TEXT,
  consent TEXT, occurred_at TEXT, ingested_at TEXT, results TEXT);
CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, user_id TEXT, kind TEXT, epistemic TEXT, statement TEXT,
  topic TEXT, context TEXT, confidence REAL, polarity INTEGER, evidence TEXT, status TEXT, user_verdict TEXT,
  superseded_by TEXT, source_agent TEXT, engine TEXT, embedding TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS observation_versions(id INTEGER PRIMARY KEY AUTOINCREMENT, observation_id TEXT, version INTEGER,
  snapshot TEXT, reason TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, user_id TEXT, type TEXT, payload TEXT, status TEXT, error TEXT,
  result TEXT, created_at TEXT, finished_at TEXT);
CREATE TABLE IF NOT EXISTS sem_concepts(term TEXT PRIMARY KEY, canonical TEXT, interpretations TEXT, source TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS sem_comparisons(id TEXT PRIMARY KEY, user_id TEXT, agent_id TEXT, concept TEXT, context TEXT,
  task TEXT, candidates TEXT, predicted TEXT, selected TEXT, selected_at TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS sem_profiles(user_id TEXT, concept TEXT, context TEXT, mean TEXT, var TEXT, n INTEGER,
  updated_at TEXT, PRIMARY KEY(user_id, concept, context));
CREATE TABLE IF NOT EXISTS sem_feedback(id TEXT PRIMARY KEY, user_id TEXT, comparison_id TEXT, concept TEXT, context TEXT,
  selected TEXT, rejected TEXT, features TEXT, predicted_p REAL, ts TEXT);
CREATE TABLE IF NOT EXISTS user_tokens(key_hash TEXT PRIMARY KEY, user_id TEXT, label TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS graph_provenance(edge_uuid TEXT PRIMARY KEY, user_id TEXT, source_id TEXT, source_type TEXT, created_at TEXT);
"""

JSON_COLS = {"scopes", "source_agents", "payload", "consent", "results", "evidence", "snapshot", "interpretations",
             "candidates", "predicted", "mean", "var", "rejected", "features", "embedding", "result", "detail"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class Store:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.conn.executescript(SCHEMA)
            self.conn.execute("PRAGMA journal_mode=WAL")

    @staticmethod
    def _enc(v):
        return json.dumps(v) if isinstance(v, (dict, list)) else v

    @staticmethod
    def _dec(row) -> dict:
        d = dict(row)
        for k, v in d.items():
            if k in JSON_COLS and isinstance(v, str):
                try:
                    d[k] = json.loads(v)
                except ValueError:
                    pass
        return d

    def exec(self, sql: str, params=()):
        with self.lock:
            cur = self.conn.execute(sql, tuple(self._enc(p) for p in params))
            self.conn.commit()
            return cur

    def query(self, sql: str, params=()) -> list[dict]:
        with self.lock:
            return [self._dec(r) for r in self.conn.execute(sql, tuple(self._enc(p) for p in params)).fetchall()]

    def one(self, sql: str, params=()) -> dict | None:
        r = self.query(sql, params)
        return r[0] if r else None

    def insert(self, table: str, row: dict):
        cols = ",".join(row)
        self.exec(f"INSERT OR REPLACE INTO {table}({cols}) VALUES({','.join('?' * len(row))})", list(row.values()))
        return row
