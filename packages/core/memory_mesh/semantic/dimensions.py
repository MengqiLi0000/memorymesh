"""Shared output-quality dimension vocabulary + deterministic text feature extractor.
Every interpretation of every ambiguous term is a vector over these dimensions, which is what lets
preferences learned on one term transfer to another (e.g. 'professional' -> 'sophisticated').
The extractor is a transparent lexical proxy (documented as such), used when no LLM is configured."""
import math, re

DIMENSIONS = {
    "novelty": "Introduces information or angles the reader likely has not seen",
    "evidence": "Specific numbers, sources, data and verifiable claims",
    "actionability": "Concrete decisions, recommendations and next steps",
    "formality": "Formal register, no slang or contractions",
    "vocabulary": "Elevated or technical vocabulary",
    "concision": "Short, dense, little filler",
    "structure": "Clear organization: sections, lists, logical sequence",
    "depth": "Causal reasoning and second-order effects",
    "nuance": "Trade-offs, caveats, conditions under which claims hold",
    "restraint": "Absence of hype, superlatives and promotional language",
    "concreteness": "Examples, named cases, specifics",
    "warmth": "Personal, conversational, human voice",
    "strategy": "Long-term framing, positioning, priorities, competitive dynamics",
    "simplicity": "Plain words and short sentences",
    "originality": "Unconventional framing or creative choices",
}
DIM_KEYS = list(DIMENSIONS)

_W = lambda *ws: re.compile(r"\b(" + "|".join(ws) + r")\b", re.I)
P = {
    "numbers": re.compile(r"\d+(?:[.,]\d+)?\s?(?:%|percent|x|bn|m|k|million|billion)?", re.I),
    "cite": _W("according to", "source", "study", "data", "survey", "report", "measured", r"\[\d+\]", "et al"),
    "imperative": re.compile(r"(?:^|[.!?]\s+|\n\s*[-*\d.]+\s*)(recommend|prioriti[sz]e|cut|launch|decide|stop|start|hire|"
                             r"focus|test|ship|raise|reduce|increase|drop|move|negotiate|build|invest|choose|do)\b", re.I),
    "action": _W("should", "next step", "next steps", "action", "decision", "we recommend", "by (?:monday|friday|q[1-4])"),
    "contraction": re.compile(r"\b\w+'(?:t|re|ll|ve|d|s|m)\b", re.I),
    "slang": _W("gonna", "wanna", "cool", "awesome", "stuff", "kinda", "super", "lol"),
    "bullet": re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.M),
    "heading": re.compile(r"^\s*(?:#+\s|[A-Z][A-Za-z ]{2,30}:\s*$)", re.M),
    "transition": _W("first", "second", "third", "finally", "therefore", "in summary", "overall"),
    "causal": _W("because", "which means", "as a result", "therefore", "driven by", "implies", "leads to", "so that"),
    "hedge": _W("however", "trade-?off", "depends", "unless", "risk", "caveat", "on the other hand", "although", "but"),
    "hype": _W("revolutionary", "best-in-class", "game-?changer", "world-class", "amazing", "incredible",
               "unprecedented", "cutting-edge", "synerg\\w*", "leverage", "unlock"),
    "cliche": _W("in today's fast-paced", "it is important to note", "at the end of the day", "think outside the box",
                 "in conclusion", "move the needle", "low-hanging fruit"),
    "novel": _W("surprisingly", "counterintuitive(?:ly)?", "contrary to", "new data", "recently", "overlooked",
                "unlike", "little-known", "most people miss"),
    "example": _W("for example", "e\\.g\\.", "for instance", "such as", "case"),
    "warm": _W("you", "your", "we", "i", "honestly", "imagine", "feel"),
    "strategic": _W("long-term", "positioning", "competitive", "moat", "priorit\\w+", "market", "strategy",
                    "strategic", "leverage point", "bet", "trade-?off"),
    "creative": _W("imagine", "metaphor", "like a", "picture", "what if"),
}


def _sq(x: float, k: float) -> float:
    return x / (x + k) if x > 0 else 0.0


def extract(text: str) -> dict[str, float]:
    words = re.findall(r"[A-Za-z']+", text)
    n = max(len(words), 1)
    sents = [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
    ns = max(len(sents), 1)
    wps = n / ns
    long_ratio = sum(len(w) >= 9 for w in words) / n
    c = {k: len(p.findall(text)) for k, p in P.items()}
    per = lambda k: c[k] / ns
    f = {
        "evidence": _sq(per("numbers") + 1.5 * per("cite"), 0.6),
        "actionability": _sq(per("imperative") + per("action"), 0.4),
        "formality": max(0.0, 1 - _sq(c["contraction"] + 2 * c["slang"], 2)) * (0.5 + 0.5 * _sq(long_ratio, 0.08)),
        "vocabulary": _sq(long_ratio, 0.12),
        "concision": 1 / (1 + math.exp((wps - 18) / 5)) * (1 / (1 + math.exp((n - 220) / 80))),
        "structure": _sq(c["bullet"] + c["heading"] + 0.5 * c["transition"], 2.5),
        "depth": _sq(per("causal"), 0.35),
        "nuance": _sq(per("hedge"), 0.4),
        "restraint": max(0.0, 1 - _sq(c["hype"] + c["cliche"] + text.count("!"), 1.5)),
        "concreteness": _sq(per("example") + 0.5 * per("numbers"), 0.5),
        "warmth": _sq(c["warm"] / n * 10, 0.6),
        "strategy": _sq(per("strategic"), 0.4),
        "simplicity": max(0.0, 1 - _sq(long_ratio, 0.1)) * (1 / (1 + math.exp((wps - 16) / 5))),
        "originality": _sq(c["creative"] + c["novel"], 1.5) * max(0.0, 1 - _sq(c["cliche"], 1)),
        "novelty": _sq(per("novel") + 0.3 * per("numbers"), 0.5) * max(0.0, 1 - _sq(c["cliche"], 1)),
    }
    return {k: round(f[k], 4) for k in DIM_KEYS}
