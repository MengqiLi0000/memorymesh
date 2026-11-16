"""Offline tests on tiny random-init models (no downloads)."""

import pytest
import torch
from transformers import GPT2Config, GPT2LMHeadModel, Qwen2Config, Qwen2ForCausalLM

from persona_lab import TRAITS, mean_difference, project, response_mean_hidden, steer
from persona_lab.metrics import formality_score, sycophancy_score


def tiny_qwen():
    torch.manual_seed(0)
    cfg = Qwen2Config(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=3,
                      num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=64)
    return Qwen2ForCausalLM(cfg).eval()


def tiny_gpt2():
    torch.manual_seed(0)
    return GPT2LMHeadModel(GPT2Config(vocab_size=64, n_embd=32, n_layer=2, n_head=4, n_positions=64)).eval()


@pytest.mark.parametrize("make", [tiny_qwen, tiny_gpt2])
def test_shapes_and_projection(make):
    model = make()
    L, H = model.config.num_hidden_layers, model.config.hidden_size
    ids = torch.randint(0, 64, (1, 12))
    acts = response_mean_hidden(model, ids, prompt_len=5)
    assert acts.shape == (L + 1, H)
    pos = torch.stack([response_mean_hidden(model, torch.randint(0, 64, (1, 10)), 4) for _ in range(3)])
    neg = torch.stack([response_mean_hidden(model, torch.randint(0, 64, (1, 10)), 4) for _ in range(3)])
    v = mean_difference(pos, neg)
    assert v.shape == (L + 1, H)
    assert project(pos, v).shape == (3, L + 1)
    assert project(pos, v, layer=1).shape == (3,)
    # projection is onto the unit vector: projecting the vector itself gives its norm
    assert torch.allclose(project(v[1], v[1]), v[1].norm(), atol=1e-5)


@pytest.mark.parametrize("make", [tiny_qwen, tiny_gpt2])
def test_steering_changes_hidden_states_and_cleans_up(make):
    model = make()
    L, H = model.config.num_hidden_layers, model.config.hidden_size
    ids = torch.randint(0, 64, (1, 8))
    vec = torch.randn(L + 1, H)
    layer = 1
    with torch.no_grad():
        base = model(ids, output_hidden_states=True).hidden_states
        with steer(model, vec, layer, coeff=4.0):
            steered = model(ids, output_hidden_states=True).hidden_states
        after = model(ids, output_hidden_states=True).hidden_states
    # layers before the hook are unchanged; the hooked layer is shifted by exactly coeff * vec
    assert torch.allclose(base[layer - 1], steered[layer - 1])
    assert torch.allclose(steered[layer] - base[layer], (4.0 * vec[layer]).expand_as(base[layer]), atol=1e-4)
    assert not torch.allclose(base[-1], steered[-1])
    # hook removed on exit
    assert torch.allclose(base[-1], after[-1])
    # coeff 0 is a no-op
    with torch.no_grad(), steer(model, vec, layer, coeff=0.0):
        zero = model(ids, output_hidden_states=True).hidden_states
    assert torch.allclose(base[-1], zero[-1])


def test_traits_and_metrics():
    assert {"formality", "sycophancy"} <= set(TRAITS)
    for t in TRAITS.values():
        assert len(t.questions) >= 10 and t.positive_instructions and t.negative_instructions
    assert formality_score("Therefore, it is essential to ensure appropriate preparation.") > \
        formality_score("hey dude, it's gonna be super fun lol!")
    assert sycophancy_score("You're absolutely right, great idea!") > \
        sycophancy_score("Actually, that's a myth and it is not true.")
