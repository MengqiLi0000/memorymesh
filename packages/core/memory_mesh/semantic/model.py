"""Hierarchical Bayesian Bradley-Terry preference model over shared dimensions.
Utility(candidate) = (w_user + w_concept + w_concept_context) . x_candidate
P(a > b) = sigmoid(w . (x_a - x_b)).  Diagonal-Gaussian posterior per level, updated online with the
standard Laplace/assumed-density step for logistic likelihoods. Established methods: Bradley-Terry (1952),
online Bayesian logistic regression (Spiegelhalter & Lauritzen 1990), uncertainty sampling for active queries."""
import math
from .dimensions import DIM_KEYS

PRIOR_VAR = {"user": 1.0, "concept": 0.5, "context": 0.25}


def sigmoid(z):
    return 1 / (1 + math.exp(-max(-30, min(30, z))))


def vec(d: dict) -> list[float]:
    return [float(d.get(k, 0.0)) for k in DIM_KEYS]


def blank(level: str) -> dict:
    return {"mean": [0.0] * len(DIM_KEYS), "var": [PRIOR_VAR[level]] * len(DIM_KEYS), "n": 0}


def predict(levels: list[dict], xa, xb) -> tuple[float, float]:
    d = [a - b for a, b in zip(xa, xb)]
    m = sum(sum(L["mean"][i] * d[i] for i in range(len(d))) for L in levels)
    v = sum(sum(L["var"][i] * d[i] * d[i] for i in range(len(d))) for L in levels)
    return sigmoid(m / math.sqrt(1 + math.pi * v / 8)), v  # probit-approximated predictive


def update(levels: list[dict], x_win, x_lose) -> float:
    d = [a - b for a, b in zip(x_win, x_lose)]
    m = sum(sum(L["mean"][i] * d[i] for i in range(len(d))) for L in levels)
    p = sigmoid(m)
    for L in levels:
        for i, di in enumerate(d):
            if di == 0:
                continue
            prec = 1 / L["var"][i] + p * (1 - p) * di * di
            L["var"][i] = 1 / prec
            L["mean"][i] += L["var"][i] * di * (1 - p)
        L["n"] += 1
    return p


def utility(levels: list[dict], x) -> float:
    return sum(sum(L["mean"][i] * x[i] for i in range(len(x))) for L in levels)


def weights(levels: list[dict]) -> dict:
    return {k: round(sum(L["mean"][i] for L in levels), 4) for i, k in enumerate(DIM_KEYS)}
