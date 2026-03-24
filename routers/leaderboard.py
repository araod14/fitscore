"""
Leaderboard router for public competition results.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import WOD, Athlete, Competition
from schemas import CompetitionLeaderboard, DivisionLeaderboard, LeaderboardEntry
from scoring import format_result, get_competition_leaderboard, get_division_leaderboard

router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])


@router.get("/{competition_id}", response_model=CompetitionLeaderboard)
async def get_full_leaderboard(
    competition_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get full leaderboard for a competition (public endpoint).
    Returns all divisions.
    """
    # Get competition
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = comp_result.scalar_one_or_none()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")

    # Get leaderboards for all divisions
    leaderboards = await get_competition_leaderboard(db, competition_id)

    # Build response
    divisions = []
    for division, entries in sorted(leaderboards.items()):
        division_entries = []
        for entry in entries:
            division_entries.append(
                LeaderboardEntry(
                    rank=entry.rank,
                    athlete_id=entry.athlete_id,
                    athlete_name=entry.athlete_name,
                    bib_number=entry.bib_number,
                    box=entry.box,
                    division=entry.division,
                    total_points=entry.total_points,
                    wod_scores=entry.wod_scores,
                )
            )
        divisions.append(
            DivisionLeaderboard(
                division=division,
                entries=division_entries,
            )
        )

    return CompetitionLeaderboard(
        competition_id=competition.id,
        competition_name=competition.name,
        updated_at=datetime.utcnow(),
        divisions=divisions,
    )


@router.get("/{competition_id}/division/{division}")
async def get_division_leaderboard_endpoint(
    competition_id: int,
    division: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get leaderboard for a specific division (public endpoint).
    """
    # Get competition
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = comp_result.scalar_one_or_none()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")

    # Get leaderboard
    entries = await get_division_leaderboard(db, competition_id, division)

    return {
        "competition_id": competition.id,
        "competition_name": competition.name,
        "division": division,
        "updated_at": datetime.utcnow().isoformat(),
        "entries": [
            {
                "rank": e.rank,
                "athlete_id": e.athlete_id,
                "athlete_name": e.athlete_name,
                "bib_number": e.bib_number,
                "box": e.box,
                "total_points": e.total_points,
                "wod_scores": e.wod_scores,
            }
            for e in entries
        ],
    }


@router.get("/{competition_id}/wods")
async def get_competition_wods(
    competition_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get WODs for a competition (public endpoint).
    Used for leaderboard headers.
    """
    result = await db.execute(
        select(WOD)
        .where(WOD.competition_id == competition_id)
        .order_by(WOD.order_in_competition)
    )
    wods = result.scalars().all()

    return [
        {
            "id": wod.id,
            "name": wod.name,
            "wod_type": wod.wod_type,
            "order": wod.order_in_competition,
            "time_cap": wod.time_cap,
            "time_cap_formatted": wod.time_cap_formatted,
        }
        for wod in wods
    ]


@router.get("/{competition_id}/divisions")
async def get_competition_divisions(
    competition_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of divisions with athletes in this competition (public endpoint).
    """
    result = await db.execute(
        select(Athlete.division)
        .where(Athlete.competition_id == competition_id)
        .distinct()
    )
    divisions = [row[0] for row in result.all()]

    return {"divisions": sorted(divisions)}


@router.get("/{competition_id}/athlete/{athlete_id}")
async def get_athlete_results(
    competition_id: int,
    athlete_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed results for a specific athlete (public endpoint).
    """
    # Get athlete
    athlete_result = await db.execute(
        select(Athlete)
        .where(Athlete.id == athlete_id, Athlete.competition_id == competition_id)
        .options(selectinload(Athlete.scores))
    )
    athlete = athlete_result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    # Get WODs
    wods_result = await db.execute(
        select(WOD)
        .where(WOD.competition_id == competition_id)
        .order_by(WOD.order_in_competition)
    )
    wods = wods_result.scalars().all()

    # Build scores list
    scores_by_wod = {s.wod_id: s for s in athlete.scores}
    total_points = 0

    results = []
    for wod in wods:
        score = scores_by_wod.get(wod.id)
        if score:
            total_points += score.points or 0
            formatted = format_result(score.raw_result, wod.wod_type, score.result_type)
            results.append(
                {
                    "wod_id": wod.id,
                    "wod_name": wod.name,
                    "wod_type": wod.wod_type,
                    "rank": score.rank,
                    "points": score.points,
                    "result": formatted,
                    "raw_result": score.raw_result,
                    "result_type": score.result_type,
                    "tiebreak": score.tiebreak,
                }
            )
        else:
            results.append(
                {
                    "wod_id": wod.id,
                    "wod_name": wod.name,
                    "wod_type": wod.wod_type,
                    "rank": None,
                    "points": 0,
                    "result": "-",
                    "raw_result": None,
                    "result_type": None,
                    "tiebreak": None,
                }
            )

    return {
        "athlete_id": athlete.id,
        "name": athlete.name,
        "bib_number": athlete.bib_number,
        "division": athlete.division,
        "box": athlete.box,
        "total_points": total_points,
        "wod_results": results,
    }


@router.get("/{competition_id}/summary")
async def get_competition_summary(
    competition_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get competition summary with top 3 per division (public endpoint).
    Useful for displaying on homepage or overview.
    """
    # Get competition
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = comp_result.scalar_one_or_none()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")

    # Get leaderboards
    leaderboards = await get_competition_leaderboard(db, competition_id)

    # Get top 3 per division
    summary = {
        "competition_id": competition.id,
        "competition_name": competition.name,
        "date": competition.date.isoformat(),
        "location": competition.location,
        "divisions": [],
    }

    for division, entries in sorted(leaderboards.items()):
        top3 = entries[:3]
        summary["divisions"].append(
            {
                "division": division,
                "top_athletes": [
                    {
                        "rank": e.rank,
                        "name": e.athlete_name,
                        "bib_number": e.bib_number,
                        "box": e.box,
                        "total_points": e.total_points,
                    }
                    for e in top3
                ],
            }
        )

    return summary
