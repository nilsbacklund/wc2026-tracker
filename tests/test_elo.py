"""World Football Elo update: worked examples."""
import math

from wc2026 import elo


def test_win_with_two_goal_margin():
    # We = 1/(1+10^(-100/400)) = 0.64006; G = 1.5
    ra, rb = elo.update(2000.0, 1900.0, 2, 0)
    delta = 60 * 1.5 * (1 - 1 / (1 + 10 ** (-100 / 400)))
    assert math.isclose(ra, 2000 + delta, rel_tol=1e-12)
    assert math.isclose(rb, 1900 - delta, rel_tol=1e-12)
    assert math.isclose(ra - 2000, 32.394, abs_tol=0.001)


def test_draw_moves_toward_underdog():
    ra, rb = elo.update(2000.0, 1900.0, 1, 1)
    assert ra < 2000 and rb > 1900  # favorite loses points on a draw
    assert math.isclose(2000 - ra, rb - 1900, rel_tol=1e-12)  # zero-sum
    assert math.isclose(2000 - ra, 8.404, abs_tol=0.001)


def test_margin_multiplier_table():
    assert elo.margin_multiplier(1, 0) == 1.0
    assert elo.margin_multiplier(0, 0) == 1.0
    assert elo.margin_multiplier(3, 1) == 1.5
    assert elo.margin_multiplier(3, 0) == (11 + 3) / 8
    assert elo.margin_multiplier(0, 5) == 2.0


def test_effective_ratings_used_for_expectation():
    # Same raw ratings, but eff_a much higher -> a is expected to win, so an
    # actual win earns fewer points than the raw-rating update would give.
    ra_eff, _ = elo.update(2000.0, 2000.0, 1, 0, eff_a=2200.0, eff_b=2000.0)
    ra_raw, _ = elo.update(2000.0, 2000.0, 1, 0)
    assert ra_eff < ra_raw
