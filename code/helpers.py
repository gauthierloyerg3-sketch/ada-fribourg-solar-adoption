"""Shared functions for the pipeline stages.

Drafted with an AI assistant, see docs/ai_log.md.
"""

import math

import numpy as np


def capture_at_k(y, score, k):
    """Share of all positives captured in the top fraction k of the ranking.

    Observations are ranked by `score` descending. The top `ceil(k * n)` are
    selected, and the result is the number of positives (y == 1) among them
    divided by the number of positives overall. Ties are broken by original
    order (stable sort), so the result is deterministic. A random ranking
    gives k in expectation.

    `y` and `score` are array-likes of equal length; 0 < k <= 1.
    Raises ValueError on unequal lengths, k outside (0, 1], or no positives.
    """
    y = np.asarray(y)
    score = np.asarray(score)
    if y.shape != score.shape or y.ndim != 1:
        raise ValueError("y and score must be 1-D arrays of equal length")
    if not 0 < k <= 1:
        raise ValueError("k must be in (0, 1]")
    positives = y == 1
    n_pos = int(positives.sum())
    if n_pos == 0:
        raise ValueError("y has no positives")
    n_top = math.ceil(k * len(y))
    order = np.argsort(-score, kind="stable")
    return float(positives[order[:n_top]].sum() / n_pos)
