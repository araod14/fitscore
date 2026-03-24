"""
FitScore Algorithm - CrossFit competition scoring system.

Scoring Rules:
- Athletes are ranked within their division for each WOD
- Points are awarded based on rank: 1st = N points (N = total athletes), last = 1
- Ties: same rank, same points, next position skipped
- No result (null) = 0 points
- Final FitScore = sum of all WOD points
- Leaderboard sorted by total points (descending)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import WODTypes
from models import WOD, Athlete, Score


@dataclass
class WODScore:
    """Represents an athlete's score for a single WOD."""

    athlete_id: int
    wod_id: int
    raw_result: Optional[float]
    tiebreak: Optional[float]
    rank: int = 0
    points: float = 0


@dataclass
class AthleteTotal:
    """Represents an athlete's total score across all WODs."""

    athlete_id: int
    athlete_name: str
    bib_number: str
    box: Optional[str]
    division: str
    total_points: float = 0
    wod_results: Dict[int, WODScore] = field(default_factory=dict)
    rank: int = 0


@dataclass
class LeaderboardEntry:
    """A single entry in the leaderboard."""

    rank: int
    athlete_id: int
    athlete_name: str
    bib_number: str
    box: Optional[str]
    division: str
    total_points: float
    wod_scores: List[Dict]  # [{wod_id, wod_name, rank, points, result, tiebreak}]


def is_higher_better(wod_type: str) -> bool:
    """
    Determine if higher values are better for this WOD type.
    Time: lower is better
    AMRAP, Load, Reps, Calories, Distance: higher is better
    """
    return wod_type in [
        WODTypes.AMRAP,
        WODTypes.LOAD,
        WODTypes.REPS,
        WODTypes.CALORIES,
        WODTypes.DISTANCE,
    ]


def calculate_wod_rankings(
    scores: List[Score], wod_type: str
) -> List[Tuple[Score, int]]:
    """
    Calculate rankings for a list of scores in a WOD.
    Returns list of (score, rank) tuples.

    Ranking rules:
    - No result (null) always ranked last with 0 points
    - Ties get same rank, next rank is skipped
    - For time: lower is better
    - For other types: higher is better
    """
    # Separate scores with results from those without
    valid_scores = []
    invalid_scores = []

    for score in scores:
        if score.raw_result is None:
            invalid_scores.append(score)
        else:
            valid_scores.append(score)

    # Sort valid scores
    higher_better = is_higher_better(wod_type)

    def sort_key(s: Score) -> Tuple:
        result = (
            s.raw_result
            if s.raw_result is not None
            else float("inf" if not higher_better else "-inf")
        )
        tiebreak = (
            s.tiebreak
            if s.tiebreak is not None
            else float("inf" if not higher_better else "-inf")
        )
        # For time: lower is better, so no negation
        # For others: higher is better, so negate for ascending sort
        if higher_better:
            return (-result, -tiebreak)
        else:
            return (result, tiebreak)

    valid_scores.sort(key=sort_key)

    # Assign ranks with tie handling
    ranked_scores = []
    current_rank = 1

    for i, score in enumerate(valid_scores):
        if i > 0:
            prev_score = valid_scores[i - 1]
            # Check if tied with previous
            same_result = score.raw_result == prev_score.raw_result
            same_tiebreak = score.tiebreak == prev_score.tiebreak
            if not (same_result and same_tiebreak):
                current_rank = i + 1
        ranked_scores.append((score, current_rank))

    # No result gets last rank (0 points)
    last_rank = len(valid_scores) + 1
    for score in invalid_scores:
        ranked_scores.append((score, last_rank))
        last_rank += 1

    return ranked_scores


def calculate_wod_points(rank: int, total_athletes: int) -> float:
    """
    Calculate points for a given rank.

    Points formula:
    - 1st place = total_athletes points
    - 2nd place = total_athletes - 1 points
    - ...
    - Last place = 1 point
    - No result = 0 points
    """
    if rank <= 0:
        return 0

    points = total_athletes - rank + 1
    return max(0, points)


async def calculate_athlete_total(
    db: AsyncSession, athlete_id: int, competition_id: int
) -> AthleteTotal:
    """
    Calculate total FitScore for a single athlete.
    """
    # Get athlete
    athlete_result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = athlete_result.scalar_one_or_none()
    if not athlete:
        raise ValueError(f"Athlete {athlete_id} not found")

    # Get all scores for this athlete
    scores_result = await db.execute(
        select(Score)
        .where(Score.athlete_id == athlete_id)
        .options(selectinload(Score.wod))
    )
    scores = scores_result.scalars().all()

    total = AthleteTotal(
        athlete_id=athlete_id,
        athlete_name=athlete.name,
        bib_number=athlete.bib_number,
        box=athlete.box,
        division=athlete.division,
    )

    for score in scores:
        if score.points is not None:
            total.total_points += score.points
            total.wod_results[score.wod_id] = WODScore(
                athlete_id=athlete_id,
                wod_id=score.wod_id,
                raw_result=score.raw_result,
                tiebreak=score.tiebreak,
                rank=score.rank or 0,
                points=score.points,
            )

    return total


async def get_division_leaderboard(
    db: AsyncSession, competition_id: int, division: str
) -> List[LeaderboardEntry]:
    """
    Get leaderboard for a specific division.
    """
    # Get all athletes in this division
    athletes_result = await db.execute(
        select(Athlete)
        .where(Athlete.competition_id == competition_id)
        .where(Athlete.division == division)
    )
    athletes = athletes_result.scalars().all()

    if not athletes:
        return []

    # Get all WODs for this competition
    wods_result = await db.execute(
        select(WOD)
        .where(WOD.competition_id == competition_id)
        .order_by(WOD.order_in_competition)
    )
    wods = wods_result.scalars().all()

    # Build athlete totals
    athlete_totals: Dict[int, AthleteTotal] = {}

    for athlete in athletes:
        athlete_totals[athlete.id] = AthleteTotal(
            athlete_id=athlete.id,
            athlete_name=athlete.name,
            bib_number=athlete.bib_number,
            box=athlete.box,
            division=athlete.division,
        )

    # Get all scores for this division's athletes
    athlete_ids = [a.id for a in athletes]
    scores_result = await db.execute(
        select(Score)
        .where(Score.athlete_id.in_(athlete_ids))
        .options(selectinload(Score.wod))
    )
    scores = scores_result.scalars().all()

    # Aggregate scores by athlete
    for score in scores:
        if score.athlete_id in athlete_totals:
            total = athlete_totals[score.athlete_id]
            if score.points is not None:
                total.total_points += score.points
            total.wod_results[score.wod_id] = WODScore(
                athlete_id=score.athlete_id,
                wod_id=score.wod_id,
                raw_result=score.raw_result,
                tiebreak=score.tiebreak,
                rank=score.rank or 0,
                points=score.points or 0,
            )

    def countback_key(athlete_total: AthleteTotal):
        """
        Tiebreaker: countback method (CrossFit standard).
        When total points are tied, rank by most 1st-place WOD finishes,
        then most 2nd-place, etc. Final tiebreaker: bib number (ascending).
        """
        wod_ranks = [
            ws.rank for ws in athlete_total.wod_results.values() if ws.rank > 0
        ]
        max_rank = len(wods) + 1
        # Count how many times each rank was achieved (lower index = better rank)
        rank_counts = [0] * max_rank
        for r in wod_ranks:
            if 1 <= r < max_rank:
                rank_counts[r] += 1
        # For sorting: negate counts so more wins = lower sort value
        countback = [-rank_counts[r] for r in range(1, max_rank)]
        return (-athlete_total.total_points, *countback, athlete_total.bib_number)

    # Sort by total points (descending), then countback tiebreaker
    sorted_athletes = sorted(athlete_totals.values(), key=countback_key)

    # Assign ranks — all positions are unique after countback
    leaderboard: List[LeaderboardEntry] = []
    current_rank = 1

    for i, athlete_total in enumerate(sorted_athletes):
        current_rank = i + 1

        # Build WOD scores list
        wod_scores = []
        for wod in wods:
            wod_result = athlete_total.wod_results.get(wod.id)
            if wod_result:
                wod_scores.append(
                    {
                        "wod_id": wod.id,
                        "wod_name": wod.name,
                        "rank": wod_result.rank,
                        "points": wod_result.points,
                        "result": wod_result.raw_result,
                        "tiebreak": wod_result.tiebreak,
                    }
                )
            else:
                wod_scores.append(
                    {
                        "wod_id": wod.id,
                        "wod_name": wod.name,
                        "rank": None,
                        "points": 0,
                        "result": None,
                        "tiebreak": None,
                    }
                )

        leaderboard.append(
            LeaderboardEntry(
                rank=current_rank,
                athlete_id=athlete_total.athlete_id,
                athlete_name=athlete_total.athlete_name,
                bib_number=athlete_total.bib_number,
                box=athlete_total.box,
                division=athlete_total.division,
                total_points=athlete_total.total_points,
                wod_scores=wod_scores,
            )
        )

    return leaderboard


async def get_competition_leaderboard(
    db: AsyncSession, competition_id: int
) -> Dict[str, List[LeaderboardEntry]]:
    """
    Get leaderboards for all divisions in a competition.
    Returns dict of {division: leaderboard}
    """
    # Get all distinct divisions in this competition
    athletes_result = await db.execute(
        select(Athlete.division)
        .where(Athlete.competition_id == competition_id)
        .distinct()
    )
    divisions = [row[0] for row in athletes_result.all()]

    leaderboards = {}
    for division in divisions:
        leaderboards[division] = await get_division_leaderboard(
            db, competition_id, division
        )

    return leaderboards


async def recalculate_wod_scores(db: AsyncSession, wod_id: int) -> int:
    """
    Recalculate rankings and points for all scores in a WOD.
    Groups by division for proper ranking.
    Returns number of scores updated.
    """
    # Get WOD info
    wod_result = await db.execute(select(WOD).where(WOD.id == wod_id))
    wod = wod_result.scalar_one_or_none()
    if not wod:
        raise ValueError(f"WOD {wod_id} not found")

    # Get all scores for this WOD with athlete info
    scores_result = await db.execute(
        select(Score).where(Score.wod_id == wod_id).options(selectinload(Score.athlete))
    )
    scores = scores_result.scalars().all()

    if not scores:
        return 0

    # Group scores by division
    division_scores: Dict[str, List[Score]] = {}
    for score in scores:
        division = score.athlete.division
        if division not in division_scores:
            division_scores[division] = []
        division_scores[division].append(score)

    updated_count = 0

    # Process each division
    for division, div_scores in division_scores.items():
        total_athletes = len(div_scores)

        # Calculate rankings
        ranked = calculate_wod_rankings(div_scores, wod.wod_type)

        # Update scores
        for score, rank in ranked:
            points = calculate_wod_points(rank, total_athletes)

            score.rank = rank
            score.points = points
            updated_count += 1

    await db.flush()
    return updated_count


async def recalculate_competition_scores(db: AsyncSession, competition_id: int) -> int:
    """
    Recalculate all rankings and points for a competition.
    Returns total number of scores updated.
    """
    # Get all WODs for this competition
    wods_result = await db.execute(
        select(WOD).where(WOD.competition_id == competition_id)
    )
    wods = wods_result.scalars().all()

    total_updated = 0
    for wod in wods:
        updated = await recalculate_wod_scores(db, wod.id)
        total_updated += updated

    return total_updated


def format_result(raw_result: Optional[float], wod_type: str) -> str:
    """
    Format a raw result for display based on WOD type.
    """
    if raw_result is None:
        return "-"

    if wod_type == WODTypes.TIME:
        # Format as mm:ss
        total_seconds = int(raw_result)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    elif wod_type == WODTypes.LOAD:
        # Format as kg with one decimal
        return f"{raw_result:.1f} kg"
    elif wod_type == WODTypes.DISTANCE:
        # Format as meters
        return f"{int(raw_result)} m"
    else:
        # AMRAP, Reps, Calories - just integer
        return str(int(raw_result))
