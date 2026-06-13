"""Match probability model: Elo logistic + Poisson goals.

All functions accept and return numpy arrays (broadcasting) so the same code
serves scalar reference computations and vectorized simulation.
"""
import numpy as np

HOST_BONUS = 60.0       # crowd/familiarity for the three hosts
AMERICAS_BONUS = 15.0   # climate/travel acclimatization
KO_COMPRESSION = 0.88   # pull KO win prob toward 0.5 (extra time/penalties)
TOTAL_GOALS = 2.75      # expected goals per group match, split by Elo
K_FACTOR = 60.0         # World Football Elo K for World Cup matches
REGULATION_MINUTES = 90.0

MODEL_PARAMS = {
    "host_bonus": HOST_BONUS,
    "americas_bonus": AMERICAS_BONUS,
    "ko_compression": KO_COMPRESSION,
    "total_goals": TOTAL_GOALS,
    "k_factor": K_FACTOR,
}


def effective_rating(elo, host, americas):
    """Elo plus host bonus, or Americas bonus for non-host Americas teams."""
    elo = np.asarray(elo, dtype=np.float64)
    host = np.asarray(host, dtype=bool)
    americas = np.asarray(americas, dtype=bool)
    return elo + HOST_BONUS * host + AMERICAS_BONUS * (americas & ~host)


def expected(ra, rb):
    """Logistic expected score of a vs b on effective ratings."""
    return 1.0 / (1.0 + 10.0 ** ((np.asarray(rb) - np.asarray(ra)) / 400.0))


def lambdas(ra, rb, minutes=REGULATION_MINUTES):
    """Poisson goal rates (la, lb) for a group match, optionally scaled to a
    fraction of the match (live conditioning on remaining minutes)."""
    e = expected(ra, rb)
    scale = minutes / REGULATION_MINUTES
    return TOTAL_GOALS * e * scale, TOTAL_GOALS * (1.0 - e) * scale


def ko_win_prob(ra, rb):
    """P(a beats b) in a knockout tie, compressed toward 0.5."""
    return 0.5 + (expected(ra, rb) - 0.5) * KO_COMPRESSION
