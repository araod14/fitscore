"""
Unit tests for scoring/fitscore.py pure functions.
No database required.
"""

from types import SimpleNamespace

from config import WODTypes
from scoring.fitscore import (
    calculate_wod_points,
    calculate_wod_rankings,
    format_result,
    is_higher_better,
)


def make_score(raw_result, tiebreak=None):
    """Create a minimal score-like object for testing."""
    return SimpleNamespace(raw_result=raw_result, tiebreak=tiebreak)


# ── is_higher_better ──────────────────────────────────────────────────────────


def test_is_higher_better_time():
    assert is_higher_better(WODTypes.TIME) is False


def test_is_higher_better_amrap():
    assert is_higher_better(WODTypes.AMRAP) is True


def test_is_higher_better_load():
    assert is_higher_better(WODTypes.LOAD) is True


def test_is_higher_better_reps():
    assert is_higher_better(WODTypes.REPS) is True


def test_is_higher_better_calories():
    assert is_higher_better(WODTypes.CALORIES) is True


def test_is_higher_better_distance():
    assert is_higher_better(WODTypes.DISTANCE) is True


# ── calculate_wod_points ──────────────────────────────────────────────────────


def test_points_first_of_five():
    assert calculate_wod_points(rank=1, total_athletes=5) == 5


def test_points_last_of_five():
    assert calculate_wod_points(rank=5, total_athletes=5) == 1


def test_points_second_of_three():
    assert calculate_wod_points(rank=2, total_athletes=3) == 2


def test_points_no_result():
    # rank=0 means no result
    assert calculate_wod_points(rank=0, total_athletes=5) == 0


def test_points_never_negative():
    # rank beyond total_athletes should not go negative
    assert calculate_wod_points(rank=10, total_athletes=5) == 0


# ── calculate_wod_rankings: time (lower is better) ────────────────────────────


def test_rankings_time_order():
    scores = [make_score(300), make_score(200), make_score(400)]
    ranked = calculate_wod_rankings(scores, WODTypes.TIME)
    by_rank = {r: s.raw_result for s, r in ranked}
    assert by_rank[1] == 200
    assert by_rank[2] == 300
    assert by_rank[3] == 400


def test_rankings_amrap_order():
    scores = [make_score(50), make_score(80), make_score(60)]
    ranked = calculate_wod_rankings(scores, WODTypes.AMRAP)
    by_rank = {r: s.raw_result for s, r in ranked}
    assert by_rank[1] == 80
    assert by_rank[2] == 60
    assert by_rank[3] == 50


def test_rankings_tie_same_rank():
    scores = [make_score(200), make_score(200), make_score(300)]
    ranked = calculate_wod_rankings(scores, WODTypes.TIME)
    ranks = sorted(r for _, r in ranked)
    # Two athletes tie at rank 1; next rank is 3
    assert ranks == [1, 1, 3]


def test_rankings_null_goes_last():
    scores = [make_score(None), make_score(300), make_score(200)]
    ranked = calculate_wod_rankings(scores, WODTypes.TIME)
    null_rank = next(r for s, r in ranked if s.raw_result is None)
    assert null_rank == 3


def test_rankings_all_null():
    scores = [make_score(None), make_score(None)]
    ranked = calculate_wod_rankings(scores, WODTypes.TIME)
    ranks = sorted(r for _, r in ranked)
    # No valid scores → last_rank starts at 1; nulls get ranks 1 and 2
    assert ranks == [1, 2]


def test_rankings_tiebreak_resolves_time():
    # Both finish in 300s; lower tiebreak wins
    scores = [make_score(300, tiebreak=50), make_score(300, tiebreak=40)]
    ranked = calculate_wod_rankings(scores, WODTypes.TIME)
    by_rank = {r: s.tiebreak for s, r in ranked}
    assert by_rank[1] == 40
    assert by_rank[2] == 50


def test_rankings_tiebreak_resolves_amrap():
    # Both score 80 reps; higher tiebreak wins
    scores = [make_score(80, tiebreak=10), make_score(80, tiebreak=20)]
    ranked = calculate_wod_rankings(scores, WODTypes.AMRAP)
    by_rank = {r: s.tiebreak for s, r in ranked}
    assert by_rank[1] == 20
    assert by_rank[2] == 10


def test_rankings_single_athlete():
    scores = [make_score(250)]
    ranked = calculate_wod_rankings(scores, WODTypes.TIME)
    assert ranked[0][1] == 1


def test_rankings_empty():
    assert calculate_wod_rankings([], WODTypes.TIME) == []


# ── format_result ─────────────────────────────────────────────────────────────


def test_format_result_none():
    assert format_result(None, WODTypes.TIME) == "-"


def test_format_result_time_exact_minutes():
    # 300 seconds = 5:00
    assert format_result(300, WODTypes.TIME) == "5:00"


def test_format_result_time_with_seconds():
    # 305 seconds = 5:05
    assert format_result(305, WODTypes.TIME) == "5:05"


def test_format_result_load():
    assert format_result(100.5, WODTypes.LOAD) == "100.5 kg"


def test_format_result_load_integer():
    assert format_result(80.0, WODTypes.LOAD) == "80.0 kg"


def test_format_result_amrap():
    assert format_result(42, WODTypes.AMRAP) == "42"


def test_format_result_reps():
    assert format_result(15, WODTypes.REPS) == "15"


def test_format_result_calories():
    assert format_result(100, WODTypes.CALORIES) == "100"


def test_format_result_distance():
    assert format_result(1500, WODTypes.DISTANCE) == "1500 m"
