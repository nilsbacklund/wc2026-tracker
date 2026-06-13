"""World Football Elo update rule (applied at full time only).

K = 60 (World Cup), goal-margin multiplier G: 1 for a margin of 0-1, 1.5 for
2, (11+N)/8 for N >= 3. The expected score uses the same effective ratings
(host/Americas bonuses) as the match model, so updates are consistent with
our predictions; this deviates slightly from eloratings.net's +100
home-advantage convention — documented trade-off.

Pure functions: idempotency (don't apply a match twice) is the storage
layer's job.
"""
from . import model


def margin_multiplier(score_a, score_b):
    n = abs(score_a - score_b)
    if n <= 1:
        return 1.0
    if n == 2:
        return 1.5
    return (11.0 + n) / 8.0


def update(rating_a, rating_b, score_a, score_b, *,
           eff_a=None, eff_b=None, k=model.K_FACTOR):
    """New (rating_a, rating_b) after a finished match.

    `eff_a`/`eff_b` are the effective ratings (with bonuses) used for the
    expectation; they default to the raw ratings.
    """
    we = float(model.expected(eff_a if eff_a is not None else rating_a,
                              eff_b if eff_b is not None else rating_b))
    w = 1.0 if score_a > score_b else 0.0 if score_a < score_b else 0.5
    delta = k * margin_multiplier(score_a, score_b) * (w - we)
    return rating_a + delta, rating_b - delta
