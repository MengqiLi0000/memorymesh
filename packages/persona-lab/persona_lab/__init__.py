"""Persona Vector Lab (experimental, optional Memory Mesh package).

Model-behavior vectors (persona vectors) for small open-weight LMs. These are NOT user
preference representations; see README.md.
"""

__version__ = "0.1.0"

from .steering import get_layers, steer
from .traits import NEUTRAL_SYSTEM_PROMPT, TRAITS, Trait, get_trait
from .vectors import (
    collect_response_activations,
    collect_trait_activations,
    extract_vectors,
    load_model,
    mean_difference,
    project,
    response_mean_hidden,
)

__all__ = [
    "Trait", "TRAITS", "get_trait", "NEUTRAL_SYSTEM_PROMPT", "extract_vectors", "load_model",
    "collect_response_activations", "collect_trait_activations", "mean_difference", "project",
    "response_mean_hidden", "steer", "get_layers",
]
