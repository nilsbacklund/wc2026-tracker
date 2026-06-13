"""Pure, vectorized 2026 World Cup Monte Carlo engine."""
from .simulate import default_spec, run_sims
from .elo import update as elo_update

__all__ = ["default_spec", "run_sims", "elo_update"]
