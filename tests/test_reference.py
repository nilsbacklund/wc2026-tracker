"""Vectorized engine vs the slow reference implementation.

Different RNG streams, so probabilities are compared statistically. At
n_ref=4000 the 3-sigma Monte Carlo band for a 20% probability is about
1.9pp; tolerances below leave headroom so the test only fires on real
logic divergence, not sampling noise.
"""
import pytest

from wc2026.simulate import run_sims
from reference_impl import run_reference


@pytest.fixture(scope="module")
def both():
    vec = run_sims(n=20000, seed=42)["probs"]
    ref_champ, ref_adv = run_reference(4000, seed=43)
    return vec, ref_champ, ref_adv


def test_champion_probabilities_agree(both):
    vec, ref_champ, _ = both
    for team in ("Spain", "Argentina", "France", "England", "Brazil",
                 "Portugal", "Sweden", "Mexico"):
        assert vec[team]["champ"] == pytest.approx(
            ref_champ.get(team, 0.0), abs=2.5), team


def test_advance_probabilities_agree(both):
    vec, _, ref_adv = both
    for team in ("Spain", "Sweden", "USA", "Haiti", "New Zealand", "Japan"):
        assert vec[team]["advance"] == pytest.approx(
            ref_adv.get(team, 0.0), abs=3.0), team


def test_group_draw_rate_sane():
    # Independent Poisson at equal strength should give ~22-29% draws.
    import numpy as np
    from wc2026 import model
    rng = np.random.default_rng(1)
    la, lb = model.lambdas(1800.0, 1800.0)
    a = rng.poisson(la, 50000)
    b = rng.poisson(lb, 50000)
    assert 0.20 < (a == b).mean() < 0.30
