"""Dev smoke run: unconditioned simulation, printed as a table.

    python -m wc2026 [n_sims]
"""
import sys
import time

from .simulate import run_sims


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    t0 = time.perf_counter()
    result = run_sims(n=n)
    dt = time.perf_counter() - t0
    probs = result["probs"]
    print(f"{n} sims in {dt:.2f}s\n")
    print(f"{'Team':<14}{'Champ%':>8}{'Final%':>8}{'Top4%':>8}{'QF%':>7}"
          f"{'R16%':>7}{'Adv%':>7}")
    print("-" * 59)
    for team in sorted(probs, key=lambda t: probs[t]["champ"], reverse=True)[:16]:
        p = probs[team]
        print(f"{team:<14}{p['champ']:>8.1f}{p['final']:>8.1f}{p['top4']:>8.1f}"
              f"{p['qf']:>7.1f}{p['r16']:>7.1f}{p['advance']:>7.1f}")


if __name__ == "__main__":
    main()
