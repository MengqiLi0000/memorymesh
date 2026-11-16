# Adapted from safety-research/persona_vectors (Apache-2.0), commit b8e0f04, modified by Memory Mesh.
# Upstream: activation_steer.py (ActivationSteerer). Changes: simplified to a function-style
# context manager, "all" positions only, layer index follows the hidden_states convention
# (vector layer l is added to the output of decoder block l-1, matching upstream's usage
# `layer_idx=layer-1` in eval_persona.py).
"""Additive activation steering via forward hooks."""

from __future__ import annotations

from contextlib import contextmanager

import torch

_LAYER_ATTRS = ("model.layers", "transformer.h", "gpt_neox.layers", "model.decoder.layers")


def get_layers(model: torch.nn.Module):
    for path in _LAYER_ATTRS:
        cur = model
        for part in path.split("."):
            cur = getattr(cur, part, None)
            if cur is None:
                break
        if cur is not None and hasattr(cur, "__getitem__"):
            return cur
    raise ValueError("Could not locate decoder layer list on model")


@contextmanager
def steer(model: torch.nn.Module, vector: torch.Tensor, layer: int, coeff: float):
    """Add `coeff * vector` to the residual stream at hidden_states index `layer` (>=1).

    `vector` may be [hidden] or the full [L+1, hidden] persona vector (row `layer` is used).
    The raw (un-normalised) mean-difference vector is used, as upstream does, so `coeff`
    is in units of the pos-neg mean difference at that layer.
    """
    if vector.ndim == 2:
        vector = vector[layer]
    layers = get_layers(model)
    if not 1 <= layer <= len(layers):
        raise IndexError(f"layer must be in [1, {len(layers)}], got {layer}")
    p = next(model.parameters())
    delta = (float(coeff) * vector).to(device=p.device, dtype=p.dtype)

    def hook(_module, _inp, out):
        if torch.is_tensor(out):
            return out + delta
        if isinstance(out, (tuple, list)) and torch.is_tensor(out[0]):
            return (out[0] + delta, *out[1:])
        return out

    # prepend=True: run before transformers' own output-capturing hooks (transformers>=5), so that
    # output_hidden_states reports the steered residual stream.
    handle = layers[layer - 1].register_forward_hook(hook, prepend=True)
    try:
        yield
    finally:
        handle.remove()
