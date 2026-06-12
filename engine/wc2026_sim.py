"""
2026 FIFA World Cup Monte Carlo simulation
- Real group draw (all 48 confirmed teams incl. March 2026 playoff winners)
- Real FIFA bracket: R32 matches 73-88, R16 89-96, QF 97-100, SF 101-102, final
- Elo-based match model with draws in group stage, knockout win probs
- Third-place qualification (best 8 of 12) with constraint-valid slot assignment
- Host advantage + Americas acclimatization bonus
"""
import random
from collections import defaultdict

random.seed(42)
N_SIMS = 20000

# Elo ratings. Top 4 anchored to footballratings.org (June 11, 2026):
# Spain 2157, Argentina 2115, France 2063, England 2024. Others estimated
# in the style of eloratings.net as of mid-2026.
ELO = {
    # Group A
    "Mexico": 1850, "South Africa": 1680, "South Korea": 1790, "Czechia": 1760,
    # Group B
    "Canada": 1810, "Bosnia": 1740, "Qatar": 1650, "Switzerland": 1860,
    # Group C
    "Brazil": 2000, "Morocco": 1900, "Haiti": 1590, "Scotland": 1780,
    # Group D
    "USA": 1840, "Paraguay": 1790, "Australia": 1760, "Turkiye": 1840,
    # Group E
    "Germany": 1955, "Curacao": 1600, "Ivory Coast": 1790, "Ecuador": 1885,
    # Group F
    "Netherlands": 1985, "Japan": 1880, "Sweden": 1810, "Tunisia": 1750,
    # Group G
    "Belgium": 1925, "Egypt": 1790, "Iran": 1800, "New Zealand": 1620,
    # Group H
    "Spain": 2157, "Cape Verde": 1640, "Saudi Arabia": 1700, "Uruguay": 1920,
    # Group I
    "France": 2063, "Senegal": 1850, "Iraq": 1690, "Norway": 1905,
    # Group J
    "Argentina": 2115, "Algeria": 1800, "Austria": 1830, "Jordan": 1680,
    # Group K
    "Portugal": 2010, "DR Congo": 1700, "Uzbekistan": 1700, "Colombia": 1935,
    # Group L
    "England": 2024, "Croatia": 1905, "Ghana": 1740, "Panama": 1740,
}

GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Turkiye"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

HOSTS = {"Mexico", "USA", "Canada"}
AMERICAS = {"Mexico", "USA", "Canada", "Brazil", "Argentina", "Uruguay",
            "Colombia", "Ecuador", "Paraguay", "Panama", "Haiti", "Curacao"}

HOST_BONUS = 60          # crowd/familiarity for the three hosts
AMERICAS_BONUS = 15      # climate/travel acclimatization for teams from the Americas

def rating(team):
    r = ELO[team]
    if team in HOSTS:
        r += HOST_BONUS
    elif team in AMERICAS:
        r += AMERICAS_BONUS
    return r

def expected(a, b):
    return 1.0 / (1.0 + 10 ** ((rating(b) - rating(a)) / 400.0))

def group_match(a, b):
    """Return points (pa, pb) for one group match, allowing draws."""
    e = expected(a, b)
    d = abs(rating(a) - rating(b))
    p_draw = max(0.06, 0.29 - d / 1400.0)   # draws rarer in mismatches
    p_a = max(0.01, e - p_draw / 2)
    p_b = max(0.01, 1 - e - p_draw / 2)
    s = p_a + p_draw + p_b
    r = random.random() * s
    if r < p_a:
        return 3, 0, a
    elif r < p_a + p_draw:
        return 1, 1, None
    else:
        return 0, 3, b

def ko_match(a, b):
    """Knockout: no draws; slight compression toward 0.5 to reflect
    extra-time/penalty randomness."""
    e = expected(a, b)
    p = 0.5 + (e - 0.5) * 0.88
    return a if random.random() < p else b

def simulate_group(teams):
    pts = {t: 0 for t in teams}
    for i in range(4):
        for j in range(i + 1, 4):
            pa, pb, _ = group_match(teams[i], teams[j])
            pts[teams[i]] += pa
            pts[teams[j]] += pb
    # tiebreak: points, then Elo + noise (proxy for goal difference)
    order = sorted(teams, key=lambda t: (pts[t], rating(t) + random.gauss(0, 60)),
                   reverse=True)
    return order, pts

# Third-place slot constraints (FIFA R32 matches with 3rd-place opponents)
THIRD_SLOTS = {
    74: set("ABCDF"),   # vs 1E
    77: set("CDFGH"),   # vs 1I
    79: set("CEFHI"),   # vs 1A
    80: set("EHIJK"),   # vs 1L
    81: set("BEFIJ"),   # vs 1D
    82: set("AEHIJ"),   # vs 1G
    85: set("EFGIJ"),   # vs 1B
    87: set("DEIJL"),   # vs 1K
}

def assign_thirds(qual_groups):
    """Backtracking perfect matching of 8 qualified 3rd-place groups to slots."""
    slots = sorted(THIRD_SLOTS, key=lambda m: len(THIRD_SLOTS[m] & set(qual_groups)))
    assignment = {}
    used = set()
    def bt(i):
        if i == len(slots):
            return True
        m = slots[i]
        cands = [g for g in qual_groups if g in THIRD_SLOTS[m] and g not in used]
        random.shuffle(cands)
        for g in cands:
            assignment[m] = g
            used.add(g)
            if bt(i + 1):
                return True
            used.discard(g)
            del assignment[m]
        return False
    if not bt(0):
        return None
    return assignment

def simulate_tournament():
    first, second, third, pts_of = {}, {}, {}, {}
    for g, teams in GROUPS.items():
        order, pts = simulate_group(teams)
        first[g], second[g], third[g] = order[0], order[1], order[2]
        pts_of[g] = pts[order[2]]
    # best 8 thirds: points, then Elo+noise
    thirds_ranked = sorted(GROUPS, key=lambda g: (pts_of[g],
                          rating(third[g]) + random.gauss(0, 60)), reverse=True)
    qual = thirds_ranked[:8]
    amap = assign_thirds(qual)
    while amap is None:  # extremely rare; reshuffle qualifiers among equals
        random.shuffle(thirds_ranked)
        qual = thirds_ranked[:8]
        amap = assign_thirds(qual)
    T = lambda m: third[amap[m]]

    # Round of 32 (matches 73-88)
    W = {}
    W[73] = ko_match(second["A"], second["B"])
    W[74] = ko_match(first["E"], T(74))
    W[75] = ko_match(first["F"], second["C"])
    W[76] = ko_match(first["C"], second["F"])
    W[77] = ko_match(first["I"], T(77))
    W[78] = ko_match(second["E"], second["I"])
    W[79] = ko_match(first["A"], T(79))
    W[80] = ko_match(first["L"], T(80))
    W[81] = ko_match(first["D"], T(81))
    W[82] = ko_match(first["G"], T(82))
    W[83] = ko_match(second["K"], second["L"])
    W[84] = ko_match(first["H"], second["J"])
    W[85] = ko_match(first["B"], T(85))
    W[86] = ko_match(first["J"], second["H"])
    W[87] = ko_match(first["K"], T(87))
    W[88] = ko_match(second["D"], second["G"])
    # Round of 16
    W[89] = ko_match(W[74], W[77])
    W[90] = ko_match(W[73], W[75])
    W[91] = ko_match(W[76], W[78])
    W[92] = ko_match(W[79], W[80])
    W[93] = ko_match(W[83], W[84])
    W[94] = ko_match(W[81], W[82])
    W[95] = ko_match(W[86], W[88])
    W[96] = ko_match(W[85], W[87])
    qf_teams = [W[m] for m in (89, 90, 91, 92, 93, 94, 95, 96)]
    # Quarterfinals
    W[97]  = ko_match(W[89], W[90])
    W[98]  = ko_match(W[93], W[94])
    W[99]  = ko_match(W[91], W[92])
    W[100] = ko_match(W[95], W[96])
    # Semifinals
    W[101] = ko_match(W[97], W[98])
    W[102] = ko_match(W[99], W[100])
    sf_losers = [t for t in (W[97], W[98], W[99], W[100]) if t not in (W[101], W[102])]
    champion = ko_match(W[101], W[102])
    runner_up = W[102] if champion == W[101] else W[101]
    third_place = ko_match(sf_losers[0], sf_losers[1])
    fourth = sf_losers[1] if third_place == sf_losers[0] else sf_losers[0]
    return champion, runner_up, third_place, fourth, qf_teams

champ = defaultdict(int); final = defaultdict(int); top4 = defaultdict(int)
qf = defaultdict(int); place3 = defaultdict(int); place4 = defaultdict(int)

for _ in range(N_SIMS):
    c, r, t3, t4, qfs = simulate_tournament()
    champ[c] += 1
    final[c] += 1; final[r] += 1
    for t in (c, r, t3, t4): top4[t] += 1
    for t in qfs: qf[t] += 1
    place3[t3] += 1; place4[t4] += 1

def pct(d, t): return 100.0 * d[t] / N_SIMS

print(f"{'Team':<14}{'Champion%':>10}{'Final%':>9}{'Top4%':>8}{'QF%':>7}")
print("-" * 48)
for t in sorted(champ, key=champ.get, reverse=True)[:16]:
    print(f"{t:<14}{pct(champ,t):>9.1f}{pct(final,t):>9.1f}{pct(top4,t):>8.1f}{pct(qf,t):>7.1f}")

print("\nMost frequent 3rd-place finishers:")
for t in sorted(place3, key=place3.get, reverse=True)[:5]:
    print(f"  {t:<14}{pct(place3,t):>5.1f}%")
print("Most frequent 4th-place finishers:")
for t in sorted(place4, key=place4.get, reverse=True)[:5]:
    print(f"  {t:<14}{pct(place4,t):>5.1f}%")

print("\nQuarterfinal (top-8) probabilities, top 12:")
for t in sorted(qf, key=qf.get, reverse=True)[:12]:
    print(f"  {t:<14}{pct(qf,t):>5.1f}%")
