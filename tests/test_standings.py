"""FIFA group ranking: points, GD, GF, then head-to-head among exact ties."""
import numpy as np

from wc2026 import standings
from wc2026.structure import GROUP_FIXTURES


def _rank(hg_list, ag_list, n=200, seed=1):
    """Rank the same real goals across n iterations; assert one stable order."""
    hg = np.tile(np.array(hg_list)[:, None], (1, n))
    ag = np.tile(np.array(ag_list)[:, None], (1, n))
    pts, gd, gf = standings.table_stats(hg, ag)
    rng = np.random.default_rng(seed)
    order = standings.rank_group(pts, gd, gf, hg, ag, rng)
    assert (order == order[:, :1]).all(), "ranking not deterministic"
    return list(order[:, 0])


def test_points_decide():
    # Fixtures: (0,1) (2,3) (0,2) (3,1) (3,0) (1,2); team 0 wins all,
    # 1 beats 2 and 3, 2 beats 3 -> 9/6/3/0 points.
    order = _rank([2, 2, 2, 0, 0, 2], [0, 0, 0, 2, 2, 0])
    assert order == [0, 1, 2, 3]


def test_goal_difference_decides_before_h2h():
    # Teams 0 and 1 both on 6 points; 1 beat 0 head-to-head but 0 has the
    # better overall GD, which FIFA applies first.
    # (0,1): 0-1   (2,3): 1-0   (0,2): 5-0   (3,1): 0-1   (3,0): 0-3   (1,2): 1-0
    # 0: pts 6, gd +7;  1: pts 9 ... adjust: make 1 lose to 2.
    # (0,1): 0-1   (2,3): 1-0   (0,2): 5-0   (3,1): 0-1   (3,0): 0-3   (1,2): 0-1
    # 0: 6 pts, gd 0-1+5+3 = +7 ; 1: 6 pts, gd +1+1-1 = +1 ; 2: 6 pts, gd
    # 1-5+1 = -3 ; 3: 0 pts. All of 0,1,2 on 6 pts, distinct GD.
    order = _rank([0, 1, 5, 0, 0, 0], [1, 0, 0, 1, 3, 1])
    assert order == [0, 1, 2, 3]


def test_head_to_head_decides_exact_ties():
    # 0 and 1 exactly tied on (pts 6, gd +2, gf 4); 0 beat 1 -> 0 first.
    # 2 and 3 exactly tied on (pts 3, gd -2, gf 2); 3 beat 2 -> 3 third.
    # (0,1): 1-0   (2,3): 0-1   (0,2): 1-2   (3,1): 1-2   (3,0): 0-2   (1,2): 2-0
    order = _rank([1, 0, 1, 1, 0, 2], [0, 1, 2, 2, 2, 0])
    assert order == [0, 1, 3, 2]


def test_table_stats_real_goal_difference():
    hg = np.array([[3], [0], [1], [0], [0], [0]])
    ag = np.array([[0], [0], [1], [0], [2], [0]])
    pts, gd, gf = standings.table_stats(hg, ag)
    # Team 0: beat 1 3-0, drew 2 1-1, beat 3 2-0 (fixture (3,0) 0-2).
    assert pts[0, 0] == 7
    assert gd[0, 0] == 5
    assert gf[0, 0] == 6
