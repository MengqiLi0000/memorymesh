"""Identity, consent grants, permission checks and audit log (enforced server-side)."""
import hashlib, hmac, secrets
from dataclasses import dataclass
from .errors import Forbidden, NotFound, Unauthorized
from .store import Store, new_id, now

SCOPES = ["memory:read", "memory:write", "graph:read", "graph:write", "human:read", "human:write",
          "semantic:read", "semantic:write", "context:read", "events:write", "mind:read"]


@dataclass
class Principal:
    kind: str  # "admin" (instance owner) | "user" (a data subject, own data only) | "agent"
    id: str

    @property
    def is_admin(self):
        return self.kind == "admin"

    def owns(self, user_id: str) -> bool:
        """Owner-level rights over user_id's data: the instance admin, or that user themself."""
        return self.kind == "admin" or (self.kind == "user" and self.id == user_id)


def _h(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class Identity:
    def __init__(self, store: Store, admin_key: str):
        self.db, self.admin_key = store, admin_key

    # --- authentication
    def authenticate(self, token: str | None) -> Principal:
        if not token:
            raise Unauthorized("Missing bearer token")
        if hmac.compare_digest(token, self.admin_key):
            return Principal("admin", "owner")
        u = self.db.one("SELECT user_id FROM user_tokens WHERE key_hash=?", [_h(token)])
        if u:
            return Principal("user", u["user_id"])
        row = self.db.one("SELECT id FROM agents WHERE key_hash=?", [_h(token)])
        if not row:
            raise Unauthorized("Invalid token")
        return Principal("agent", row["id"])

    # --- agents
    def create_agent(self, name: str, description: str = "", agent_id: str | None = None) -> dict:
        key = "mm_" + secrets.token_urlsafe(24)
        aid = agent_id or new_id("agt")
        if self.db.one("SELECT 1 FROM agents WHERE id=?", [aid]):
            raise Forbidden(f"agent {aid} already exists")
        self.db.insert("agents", {"id": aid, "name": name, "description": description, "key_hash": _h(key),
                                  "created_at": now()})
        return {"id": aid, "name": name, "description": description, "api_key": key,
                "note": "Store the api_key now; only its hash is kept."}

    def create_user_token(self, user_id: str, label: str = "") -> dict:
        key = "mu_" + secrets.token_urlsafe(24)
        self.db.insert("user_tokens", {"key_hash": _h(key), "user_id": user_id, "label": label, "created_at": now()})
        return {"user_id": user_id, "api_key": key}

    def list_agents(self):
        return self.db.query("SELECT id,name,description,created_at FROM agents ORDER BY created_at")

    # --- grants (explicit consent records)
    def grant(self, user_id: str, agent_id: str, scopes: list[str], source_agents: list[str] | None = None,
              note: str = "") -> dict:
        if not self.db.one("SELECT 1 FROM agents WHERE id=?", [agent_id]):
            raise NotFound(f"agent {agent_id} not found")
        bad = [s for s in scopes if s not in SCOPES and s != "*"]
        if bad:
            raise Forbidden(f"unknown scopes {bad}", allowed=SCOPES)
        g = {"id": new_id("grt"), "user_id": user_id, "agent_id": agent_id, "scopes": scopes,
             "source_agents": source_agents or [agent_id], "note": note, "created_at": now(), "revoked_at": None}
        self.db.insert("grants", g)
        self.audit("owner", user_id, "grant.create", g["id"], True, {"agent": agent_id, "scopes": scopes})
        return g

    def revoke(self, grant_id: str) -> dict:
        g = self.db.one("SELECT * FROM grants WHERE id=?", [grant_id])
        if not g:
            raise NotFound("grant not found")
        self.db.exec("UPDATE grants SET revoked_at=? WHERE id=?", [now(), grant_id])
        self.audit("owner", g["user_id"], "grant.revoke", grant_id, True, {})
        return self.db.one("SELECT * FROM grants WHERE id=?", [grant_id])

    def grants(self, user_id: str | None = None, agent_id: str | None = None, active_only=False):
        q, p = "SELECT * FROM grants WHERE 1=1", []
        if user_id:
            q += " AND user_id=?"; p.append(user_id)
        if agent_id:
            q += " AND agent_id=?"; p.append(agent_id)
        if active_only:
            q += " AND revoked_at IS NULL"
        return self.db.query(q + " ORDER BY created_at", p)

    # --- authorization
    def authorize(self, pr: Principal, user_id: str, scope: str, resource: str = "") -> set[str] | None:
        """Returns the set of agent ids whose data the principal may read (None = unrestricted)."""
        if pr.owns(user_id):
            self.audit(pr.id, user_id, scope, resource, True, {})
            return None
        if pr.kind == "user":
            self.audit(pr.id, user_id, scope, resource, False, {"reason": "user tokens only access their own data"})
            raise Forbidden("a user token can only access its own data")
        gs = [g for g in self.grants(user_id, pr.id, active_only=True)
              if scope in g["scopes"] or "*" in g["scopes"]]
        if not gs:
            self.audit(pr.id, user_id, scope, resource, False, {"reason": "no active grant"})
            raise Forbidden(f"agent {pr.id} has no active '{scope}' grant for user {user_id}")
        sources: set[str] = set()
        for g in gs:
            if "*" in g["source_agents"]:
                self.audit(pr.id, user_id, scope, resource, True, {"grant": g["id"]})
                return None
            sources.update(g["source_agents"])
        sources.add(pr.id)
        self.audit(pr.id, user_id, scope, resource, True, {"grants": [g["id"] for g in gs]})
        return sources

    def audit(self, actor, user_id, action, resource, allowed, detail):
        self.db.exec("INSERT INTO audit(ts,actor,user_id,action,resource,allowed,detail) VALUES(?,?,?,?,?,?,?)",
                     [now(), actor, user_id, action, resource, int(allowed), detail])

    def audit_log(self, user_id: str | None = None, limit: int = 200):
        if user_id:
            return self.db.query("SELECT * FROM audit WHERE user_id=? ORDER BY id DESC LIMIT ?", [user_id, limit])
        return self.db.query("SELECT * FROM audit ORDER BY id DESC LIMIT ?", [limit])
