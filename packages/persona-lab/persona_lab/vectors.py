# Adapted from safety-research/persona_vectors (Apache-2.0), commit b8e0f04, modified by Memory Mesh.
# Upstream: generate_vec.py (get_hidden_p_and_r / save_persona_vector, "response_avg_diff").
# Changes: no LLM-judge filtering step, in-memory API, batched generation with a chat template,
# per-question activation caching so different question splits can reuse the same forward passes,
# projection helper for monitoring.
"""Persona vector extraction (mean difference of response activations) and projection."""

from __future__ import annotations

from dataclasses import dataclass

import torch

from .traits import Trait, get_trait


def pick_device(device: str | None = None) -> str:
    if device:
        return device
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_model(model_name: str, device: str | None = None, dtype: torch.dtype = torch.float32):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = pick_device(device)
    tok = AutoTokenizer.from_pretrained(model_name)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name, dtype=dtype).to(device)
    model.eval()
    return model, tok


def build_prompt(tokenizer, system: str, question: str) -> str:
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


@torch.no_grad()
def generate(model, tokenizer, prompts: list[str], max_new_tokens: int = 64, batch_size: int = 16) -> list[str]:
    """Greedy, batched generation (deterministic given model + prompts)."""
    out: list[str] = []
    for i in range(0, len(prompts), batch_size):
        chunk = prompts[i : i + batch_size]
        enc = tokenizer(chunk, return_tensors="pt", padding=True, add_special_tokens=False).to(model.device)
        gen = model.generate(
            **enc,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )
        for row in gen[:, enc["input_ids"].shape[1] :]:
            out.append(tokenizer.decode(row, skip_special_tokens=True).strip())
    return out


@torch.no_grad()
def response_mean_hidden(model, input_ids: torch.Tensor, prompt_len: int) -> torch.Tensor:
    """Mean hidden state over response tokens for every layer.

    input_ids: [1, T] (prompt followed by response). Returns [num_layers+1, hidden] (float32, cpu).
    Index 0 is the embedding output; index l>=1 is the output of decoder block l-1
    (HF convention: the last entry has the final norm applied).
    """
    outputs = model(input_ids=input_ids.to(model.device), output_hidden_states=True)
    hs = outputs.hidden_states
    if input_ids.shape[1] <= prompt_len:
        raise ValueError("empty response")
    return torch.stack([h[0, prompt_len:, :].mean(0).float().cpu() for h in hs], dim=0)


def collect_response_activations(model, tokenizer, prompts: list[str], responses: list[str]) -> torch.Tensor:
    """Returns [N, num_layers+1, hidden]: per-example response-averaged activations."""
    acts = []
    for p, r in zip(prompts, responses):
        p_ids = tokenizer(p, return_tensors="pt", add_special_tokens=False)["input_ids"]
        full = tokenizer(p + r, return_tensors="pt", add_special_tokens=False)["input_ids"]
        if full.shape[1] <= p_ids.shape[1]:  # degenerate empty response: append eos so we have >=1 token
            full = torch.cat([p_ids, torch.tensor([[tokenizer.eos_token_id]])], dim=1)
        acts.append(response_mean_hidden(model, full, p_ids.shape[1]))
    return torch.stack(acts, dim=0)


def mean_difference(pos_acts: torch.Tensor, neg_acts: torch.Tensor) -> torch.Tensor:
    """Persona vector per layer: mean(pos) - mean(neg). Inputs [N, L+1, H] -> [L+1, H]."""
    return pos_acts.float().mean(0) - neg_acts.float().mean(0)


def project(acts: torch.Tensor, vector: torch.Tensor, layer: int | None = None) -> torch.Tensor:
    """Scalar projection of activations onto the (unit-normalised) persona vector.

    - acts [N, L+1, H], vector [L+1, H], layer=None -> [N, L+1]
    - acts [N, L+1, H], vector [L+1, H], layer=l    -> [N]
    - acts [..., H], vector [H]                     -> [...]
    """
    acts = acts.float()
    vector = vector.float()
    if vector.ndim == 1:
        return acts @ (vector / vector.norm().clamp_min(1e-8))
    unit = vector / vector.norm(dim=-1, keepdim=True).clamp_min(1e-8)
    if layer is not None:
        return acts[:, layer, :] @ unit[layer]
    return (acts * unit.unsqueeze(0)).sum(-1)


@dataclass
class TraitActivations:
    """Cached per-question pos/neg responses and activations for one trait."""

    trait: str
    questions: list[str]
    pos_responses: list[str]
    neg_responses: list[str]
    pos_acts: torch.Tensor  # [Q, L+1, H]
    neg_acts: torch.Tensor  # [Q, L+1, H]

    def vector(self, idx: list[int]) -> torch.Tensor:
        return mean_difference(self.pos_acts[idx], self.neg_acts[idx])


def collect_trait_activations(model, tokenizer, trait: Trait | str, max_new_tokens: int = 64) -> TraitActivations:
    trait = get_trait(trait) if isinstance(trait, str) else trait
    qs = list(trait.questions)
    pos_sys = [trait.positive_instructions[i % len(trait.positive_instructions)] for i in range(len(qs))]
    neg_sys = [trait.negative_instructions[i % len(trait.negative_instructions)] for i in range(len(qs))]
    pos_prompts = [build_prompt(tokenizer, s, q) for s, q in zip(pos_sys, qs)]
    neg_prompts = [build_prompt(tokenizer, s, q) for s, q in zip(neg_sys, qs)]
    pos_resp = generate(model, tokenizer, pos_prompts, max_new_tokens)
    neg_resp = generate(model, tokenizer, neg_prompts, max_new_tokens)
    return TraitActivations(
        trait=trait.name,
        questions=qs,
        pos_responses=pos_resp,
        neg_responses=neg_resp,
        pos_acts=collect_response_activations(model, tokenizer, pos_prompts, pos_resp),
        neg_acts=collect_response_activations(model, tokenizer, neg_prompts, neg_resp),
    )


def extract_vectors(model_name: str, trait: str, device: str | None = None, max_new_tokens: int = 64,
                    model=None, tokenizer=None) -> torch.Tensor:
    """Extract a persona vector for `trait` using all its questions. Returns [num_layers+1, hidden]."""
    if model is None or tokenizer is None:
        model, tokenizer = load_model(model_name, device)
    ta = collect_trait_activations(model, tokenizer, trait, max_new_tokens)
    return ta.vector(list(range(len(ta.questions))))
