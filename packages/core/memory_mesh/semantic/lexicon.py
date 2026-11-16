"""Seed lexicon of ambiguous evaluative language. Each interpretation is an operational reading
(an instruction a model can follow) plus a vector over the shared dimensions.
Original Memory Mesh content; extended at runtime by LLM-generated interpretations (stored in sem_concepts)."""

def I(id, label, instruction, **dims):
    return {"id": id, "label": label, "instruction": instruction, "dims": dims}

SEED = {
    "sophisticated": [
        I("insight", "Deeper insight", "Add non-obvious insight and second-order reasoning; cut what the reader already knows.",
          novelty=1, depth=1, evidence=.5),
        I("register", "Elevated register", "Use a more formal, refined register and precise vocabulary.",
          vocabulary=1, formality=1),
        I("nuance", "More nuance", "Acknowledge trade-offs, conditions and uncertainty instead of flat claims.",
          nuance=1, depth=.5, restraint=.5),
        I("rigor", "Evidence-led", "Ground each claim in specific data, sources or numbers.", evidence=1, concreteness=.6),
    ],
    "professional": [
        I("precision", "Factual precision", "Replace vague claims with precise, verifiable statements.", evidence=1, concreteness=.5),
        I("organized", "Logical organization", "Restructure into a clear sequence with headings or numbered points.", structure=1, concision=.4),
        I("formal", "Formal tone", "Use formal language; remove slang, contractions and jokes.", formality=1, vocabulary=.4),
        I("sober", "Less promotional", "Remove hype and superlatives; state things plainly.", restraint=1, nuance=.3),
    ],
    "insightful": [
        I("novel", "New information", "Surface facts or angles the reader is unlikely to know.", novelty=1, evidence=.5),
        I("causal", "Explains why", "Explain causes and mechanisms, not just observations.", depth=1),
        I("implication", "So-what", "Spell out the decision implications of each point.", actionability=1, strategy=.5),
    ],
    "elegant": [
        I("economy", "Economy", "Say it in fewer words with no loss of meaning.", concision=1, simplicity=.5),
        I("flow", "Flow", "Make transitions seamless and the argument read as one line of thought.", structure=.6, warmth=.3),
        I("refined", "Refined language", "Choose more refined, precise wording.", vocabulary=1, formality=.5),
    ],
    "improve": [
        I("clarity", "Clearer", "Make it easier to understand on first read.", simplicity=1, structure=.5),
        I("substance", "More substance", "Add evidence and reasoning.", evidence=.8, depth=.8),
        I("actionable", "More useful", "Turn observations into recommendations.", actionability=1),
    ],
    "optimize": [
        I("shorter", "Tighter", "Cut length while keeping all key content.", concision=1),
        I("decisive", "Decision-focused", "Optimize for the decision the reader must make.", actionability=1, strategy=.6),
        I("measurable", "Measurable", "Attach metrics and targets.", evidence=1, concreteness=.5),
    ],
    "simplify": [
        I("plain", "Plain language", "Use common words and short sentences.", simplicity=1),
        I("fewer", "Fewer ideas", "Keep only the most important points.", concision=1, restraint=.3),
        I("structure", "Clearer structure", "Break it into steps or bullets.", structure=1),
    ],
    "refine": [
        I("polish", "Polish wording", "Improve word choice and rhythm without changing content.", vocabulary=.6, concision=.5),
        I("sharpen", "Sharpen argument", "Make the core claim crisper and better supported.", evidence=.6, depth=.6),
        I("trim", "Trim", "Remove redundancy.", concision=1),
    ],
    "value": [
        I("decision", "Decision value", "Maximize what the reader can act on.", actionability=1),
        I("information", "Information value", "Maximize new, accurate information.", novelty=1, evidence=.7),
        I("strategic", "Strategic value", "Connect to long-term priorities.", strategy=1),
    ],
    "depth": [
        I("mechanism", "Mechanisms", "Explain the underlying mechanisms.", depth=1),
        I("evidence", "Evidence", "Bring more data to each point.", evidence=1),
        I("tradeoffs", "Trade-offs", "Explore trade-offs and edge cases.", nuance=1),
    ],
    "quality": [
        I("correct", "Accuracy", "Prioritize correctness and verifiable claims.", evidence=1, restraint=.4),
        I("useful", "Usefulness", "Prioritize practical usefulness.", actionability=1, concreteness=.5),
        I("crafted", "Craft", "Prioritize polished writing.", structure=.6, vocabulary=.5),
    ],
    "creativity": [
        I("unexpected", "Unexpected framing", "Use an unconventional angle or metaphor.", originality=1),
        I("voice", "Distinct voice", "Write with personality.", warmth=1, originality=.5),
        I("ideas", "Novel ideas", "Propose options nobody listed yet.", novelty=1, originality=.6),
    ],
    "better": [
        I("clearer", "Clearer", "Make it clearer and better structured.", simplicity=.7, structure=.7),
        I("richer", "More substantive", "Add evidence and insight.", evidence=.7, novelty=.7),
        I("useful", "More actionable", "Make it decision-ready.", actionability=1),
    ],
    "less generic": [
        I("specific", "Specific details", "Replace generalities with specific numbers, names and cases.", concreteness=1, evidence=.6),
        I("novel", "Non-obvious content", "Remove points any reader would already expect.", novelty=1, restraint=.4),
        I("voice", "Distinct voice", "Give it a recognizable voice.", originality=1, warmth=.5),
    ],
    "more human": [
        I("warm", "Warmer", "Write conversationally, addressing the reader directly.", warmth=1, formality=-.5),
        I("plain", "Plainer", "Drop jargon and stiff phrasing.", simplicity=1, vocabulary=-.5),
        I("story", "Storytelling", "Use a concrete anecdote or example.", concreteness=1, originality=.4),
    ],
    "more strategic": [
        I("longterm", "Long-term framing", "Frame around long-term positioning.", strategy=1),
        I("priorities", "Priorities", "Rank options and state what not to do.", actionability=.8, strategy=.6),
        I("competitive", "Competitive dynamics", "Analyze competitors and market structure.", strategy=.8, depth=.6),
    ],
}

GENERIC = [
    I("concise", "More concise", "Make it shorter and denser.", concision=1),
    I("detailed", "More detailed", "Add detail, evidence and examples.", evidence=.7, concreteness=.7),
    I("structured", "Better structured", "Organize it more clearly.", structure=1),
]

# multilingual / phrasal aliases -> canonical term
ALIASES = {
    "sophistication": "sophisticated", "sofisticado": "sophisticated", "sofisticada": "sophisticated",
    "sophistiqué": "sophisticated", "anspruchsvoll": "sophisticated", "高级": "sophisticated", "高端": "sophisticated",
    "有深度": "depth", "professionally": "professional", "profesional": "professional", "professionnel": "professional",
    "professionell": "professional", "专业": "professional", "insight": "insightful", "有洞察": "insightful",
    "elegance": "elegant", "elegante": "elegant", "优雅": "elegant", "improve": "improve", "improved": "improve",
    "优化": "optimize", "简化": "simplify", "make it better": "better", "make this better": "better",
    "更好": "better", "less generic": "less generic", "不那么泛泛": "less generic", "more human": "more human",
    "更有人情味": "more human", "more strategic": "more strategic", "更有战略性": "more strategic",
    "creative": "creativity", "有创意": "creativity", "high quality": "quality", "有价值": "value",
}
