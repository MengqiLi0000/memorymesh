"""LLM access. Reuses Mem0's provider abstraction (mem0.utils.factory.LlmFactory),
so every provider Mem0 supports (openai, anthropic, ollama, litellm, gemini, groq, ...)
works here without new provider code."""
import json, re
from .config import Settings
from .errors import Unavailable

DEFAULT_MODELS = {"openai": "gpt-4.1-mini", "anthropic": "claude-sonnet-5-5", "ollama": "llama3.1",
                  "gemini": "gemini-2.5-flash", "groq": "llama-3.3-70b-versatile"}


def mem0_llm_config(s: Settings) -> dict:
    if not s.llm_enabled:
        # Mem0 instantiates an LLM eagerly; with no provider we never call it (infer=False everywhere).
        return {"provider": "openai", "config": {"api_key": "offline-mode-no-llm", "model": "gpt-4.1-mini"}}
    cfg = {"model": s.llm_model or DEFAULT_MODELS.get(s.llm_provider, "gpt-4.1-mini"), "temperature": 0.1}
    if s.llm_api_key:
        cfg["api_key"] = s.llm_api_key
    return {"provider": s.llm_provider, "config": cfg}


class LLM:
    def __init__(self, s: Settings):
        self.s = s
        self._llm = None
        if s.llm_enabled:
            from mem0.utils.factory import LlmFactory
            c = mem0_llm_config(s)
            self._llm = LlmFactory.create(c["provider"], c["config"])

    @property
    def enabled(self) -> bool:
        return self._llm is not None

    @property
    def engine(self) -> str:
        return f"llm:{self.s.llm_provider}" if self.enabled else "heuristic"

    def require(self, feature: str):
        if not self.enabled:
            raise Unavailable(f"{feature} requires an LLM. Set MESH_LLM_PROVIDER (and an API key).", feature=feature)

    def text(self, system: str, user: str) -> str:
        self.require("llm")
        return self._llm.generate_response(messages=[{"role": "system", "content": system},
                                                     {"role": "user", "content": user}])

    def json(self, system: str, user: str) -> dict | list:
        self.require("llm")
        try:
            raw = self._llm.generate_response(
                messages=[{"role": "system", "content": system + "\nRespond with JSON only."},
                          {"role": "user", "content": user}], response_format={"type": "json_object"})
        except TypeError:
            raw = self.text(system + "\nRespond with JSON only.", user)
        return parse_json(raw)


def parse_json(raw: str):
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        return json.loads(raw)
    except ValueError:
        m = re.search(r"(\{.*\}|\[.*\])", raw, re.S)
        if not m:
            raise
        return json.loads(m.group(1))
