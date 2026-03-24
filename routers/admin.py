"""
Admin router for managing competitions, athletes, and WODs.
"""

import csv
import io
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from database import get_db
from models import User, Competition, Athlete, WOD, WODStandard, Score
from schemas import (
    CompetitionCreate, CompetitionUpdate, CompetitionResponse, CompetitionListResponse,
    AthleteCreate, AthleteUpdate, AthleteResponse, AthleteListResponse, AthleteImportResult,
    WODCreate, WODUpdate, WODResponse, WODListResponse, WODStandardCreate, WODStandardResponse,
    DashboardStats,
)
from auth import get_current_admin, get_current_judge_or_admin
from config import DIVISIONS, GENDERS

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ============== Competitions ==============

@router.get("/competitions", response_model=CompetitionListResponse)
async def list_competitions(
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    is_active: Optional[bool] = None,
):
    """
    List all competitions with pagination.
    """
    query = select(Competition)

    if is_active is not None:
        query = query.where(Competition.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get items
    query = query.order_by(Competition.date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    competitions = result.scalars().all()

    # Add counts
    items = []
    for comp in competitions:
        # Count athletes
        athlete_count_result = await db.execute(
            select(func.count()).where(Athlete.competition_id == comp.id)
        )
        athlete_count = athlete_count_result.scalar()

        # Count WODs
        wod_count_result = await db.execute(
            select(func.count()).where(WOD.competition_id == comp.id)
        )
        wod_count = wod_count_result.scalar()

        items.append(CompetitionResponse(
            id=comp.id,
            name=comp.name,
            description=comp.description,
            date=comp.date,
            location=comp.location,
            is_active=comp.is_active,
            created_at=comp.created_at,
            created_by=comp.created_by,
            athlete_count=athlete_count,
            wod_count=wod_count,
        ))

    return CompetitionListResponse(items=items, total=total)


@router.post("/competitions", response_model=CompetitionResponse, status_code=status.HTTP_201_CREATED)
async def create_competition(
    competition: CompetitionCreate,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new competition.
    """
    comp = Competition(
        name=competition.name,
        description=competition.description,
        date=competition.date,
        location=competition.location,
        created_by=current_user.id,
    )
    db.add(comp)
    await db.flush()
    await db.refresh(comp)

    return CompetitionResponse(
        id=comp.id,
        name=comp.name,
        description=comp.description,
        date=comp.date,
        location=comp.location,
        is_active=comp.is_active,
        created_at=comp.created_at,
        created_by=comp.created_by,
        athlete_count=0,
        wod_count=0,
    )


@router.get("/competitions/{competition_id}", response_model=CompetitionResponse)
async def get_competition(
    competition_id: int,
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific competition.
    """
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")

    # Count athletes and WODs
    athlete_count_result = await db.execute(
        select(func.count()).where(Athlete.competition_id == comp.id)
    )
    athlete_count = athlete_count_result.scalar()

    wod_count_result = await db.execute(
        select(func.count()).where(WOD.competition_id == comp.id)
    )
    wod_count = wod_count_result.scalar()

    return CompetitionResponse(
        id=comp.id,
        name=comp.name,
        description=comp.description,
        date=comp.date,
        location=comp.location,
        is_active=comp.is_active,
        created_at=comp.created_at,
        created_by=comp.created_by,
        athlete_count=athlete_count,
        wod_count=wod_count,
    )


@router.put("/competitions/{competition_id}", response_model=CompetitionResponse)
async def update_competition(
    competition_id: int,
    competition: CompetitionUpdate,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Update a competition.
    """
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")

    if competition.name is not None:
        comp.name = competition.name
    if competition.description is not None:
        comp.description = competition.description
    if competition.date is not None:
        comp.date = competition.date
    if competition.location is not None:
        comp.location = competition.location
    if competition.is_active is not None:
        comp.is_active = competition.is_active

    await db.flush()
    await db.refresh(comp)

    # Get counts
    athlete_count_result = await db.execute(
        select(func.count()).where(Athlete.competition_id == comp.id)
    )
    wod_count_result = await db.execute(
        select(func.count()).where(WOD.competition_id == comp.id)
    )

    return CompetitionResponse(
        id=comp.id,
        name=comp.name,
        description=comp.description,
        date=comp.date,
        location=comp.location,
        is_active=comp.is_active,
        created_at=comp.created_at,
        created_by=comp.created_by,
        athlete_count=athlete_count_result.scalar(),
        wod_count=wod_count_result.scalar(),
    )


@router.delete("/competitions/{competition_id}")
async def delete_competition(
    competition_id: int,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a competition and all related data.
    """
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")

    await db.delete(comp)
    return {"message": "Competition deleted successfully"}


# ============== Athletes ==============

@router.get("/competitions/{competition_id}/athletes", response_model=AthleteListResponse)
async def list_athletes(
    competition_id: int,
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    division: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    List athletes in a competition.
    """
    query = select(Athlete).where(Athlete.competition_id == competition_id)

    if division:
        query = query.where(Athlete.division == division)
    if search:
        query = query.where(
            (Athlete.name.ilike(f"%{search}%")) |
            (Athlete.bib_number.ilike(f"%{search}%"))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get items
    query = query.order_by(Athlete.bib_number).offset(skip).limit(limit)
    result = await db.execute(query)
    athletes = result.scalars().all()

    return AthleteListResponse(items=athletes, total=total)


@router.post("/athletes", response_model=AthleteResponse, status_code=status.HTTP_201_CREATED)
async def create_athlete(
    athlete: AthleteCreate,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new athlete.
    """
    # Check competition exists
    comp_result = await db.execute(
        select(Competition).where(Competition.id == athlete.competition_id)
    )
    if not comp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Competition not found")

    # Check bib_number uniqueness
    existing = await db.execute(
        select(Athlete).where(
            Athlete.competition_id == athlete.competition_id,
            Athlete.bib_number == athlete.bib_number
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Bib number {athlete.bib_number} already exists in this competition"
        )

    new_athlete = Athlete(
        name=athlete.name,
        gender=athlete.gender,
        birth_date=athlete.birth_date,
        category=athlete.category,
        division=athlete.division,
        box=athlete.box,
        email=athlete.email,
        phone=athlete.phone,
        bib_number=athlete.bib_number,
        competition_id=athlete.competition_id,
    )
    db.add(new_athlete)
    await db.flush()
    await db.refresh(new_athlete)
    return new_athlete


@router.get("/athletes/{athlete_id}", response_model=AthleteResponse)
async def get_athlete(
    athlete_id: int,
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific athlete.
    """
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return athlete


@router.put("/athletes/{athlete_id}", response_model=AthleteResponse)
async def update_athlete(
    athlete_id: int,
    athlete_update: AthleteUpdate,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Update an athlete.
    """
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    # Check bib_number uniqueness if changing
    if athlete_update.bib_number and athlete_update.bib_number != athlete.bib_number:
        existing = await db.execute(
            select(Athlete).where(
                Athlete.competition_id == athlete.competition_id,
                Athlete.bib_number == athlete_update.bib_number
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Bib number {athlete_update.bib_number} already exists"
            )

    for field, value in athlete_update.model_dump(exclude_unset=True).items():
        setattr(athlete, field, value)

    await db.flush()
    await db.refresh(athlete)
    return athlete


@router.delete("/athletes/{athlete_id}")
async def delete_athlete(
    athlete_id: int,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an athlete and their scores.
    """
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    await db.delete(athlete)
    return {"message": "Athlete deleted successfully"}


@router.post("/competitions/{competition_id}/athletes/import", response_model=AthleteImportResult)
async def import_athletes_csv(
    competition_id: int,
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_admin)] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Import athletes from CSV file.
    Expected columns: name, gender, birth_date, division, box, bib_number
    """
    # Check competition exists
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    if not comp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Competition not found")

    # Read and parse CSV
    content = await file.read()
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))

    success_count = 0
    error_count = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            # Validate required fields
            name = row.get("name", "").strip()
            gender = row.get("gender", "").strip()
            division = row.get("division", "").strip()
            bib_number = row.get("bib_number", "").strip()

            if not name:
                raise ValueError("Name is required")
            if gender not in GENDERS:
                raise ValueError(f"Invalid gender: {gender}")
            if division not in DIVISIONS:
                raise ValueError(f"Invalid division: {division}")
            if not bib_number:
                raise ValueError("Bib number is required")

            # Check bib uniqueness
            existing = await db.execute(
                select(Athlete).where(
                    Athlete.competition_id == competition_id,
                    Athlete.bib_number == bib_number
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Bib number {bib_number} already exists")

            # Parse birth_date
            birth_date = None
            if row.get("birth_date"):
                try:
                    birth_date = datetime.strptime(row["birth_date"], "%Y-%m-%d").date()
                except ValueError:
                    pass  # Ignore invalid dates

            athlete = Athlete(
                name=name,
                gender=gender,
                birth_date=birth_date,
                division=division,
                box=row.get("box", "").strip() or None,
                bib_number=bib_number,
                competition_id=competition_id,
            )
            db.add(athlete)
            success_count += 1

        except Exception as e:
            error_count += 1
            errors.append(f"Row {row_num}: {str(e)}")

    await db.flush()

    return AthleteImportResult(
        success_count=success_count,
        error_count=error_count,
        errors=errors[:50],  # Limit errors to first 50
    )


# ============== WODs ==============

@router.get("/competitions/{competition_id}/wods", response_model=WODListResponse)
async def list_wods(
    competition_id: int,
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    List WODs in a competition.
    """
    result = await db.execute(
        select(WOD)
        .where(WOD.competition_id == competition_id)
        .options(selectinload(WOD.standards))
        .order_by(WOD.order_in_competition)
    )
    wods = result.scalars().all()

    return WODListResponse(items=wods, total=len(wods))


@router.post("/wods", response_model=WODResponse, status_code=status.HTTP_201_CREATED)
async def create_wod(
    wod: WODCreate,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new WOD with optional standards.
    """
    # Check competition exists
    comp_result = await db.execute(
        select(Competition).where(Competition.id == wod.competition_id)
    )
    if not comp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Competition not found")

    new_wod = WOD(
        name=wod.name,
        description=wod.description,
        wod_type=wod.wod_type,
        time_cap=wod.time_cap,
        order_in_competition=wod.order_in_competition,
        competition_id=wod.competition_id,
    )
    db.add(new_wod)
    await db.flush()

    # Add standards if provided
    if wod.standards:
        for std in wod.standards:
            standard = WODStandard(
                wod_id=new_wod.id,
                division=std.division,
                rx_weight_kg=std.rx_weight_kg,
                description_override=std.description_override,
            )
            db.add(standard)

    await db.flush()
    await db.refresh(new_wod)

    # Load standards
    result = await db.execute(
        select(WOD)
        .where(WOD.id == new_wod.id)
        .options(selectinload(WOD.standards))
    )
    return result.scalar_one()


@router.get("/wods/{wod_id}", response_model=WODResponse)
async def get_wod(
    wod_id: int,
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific WOD.
    """
    result = await db.execute(
        select(WOD)
        .where(WOD.id == wod_id)
        .options(selectinload(WOD.standards))
    )
    wod = result.scalar_one_or_none()
    if not wod:
        raise HTTPException(status_code=404, detail="WOD not found")
    return wod


@router.put("/wods/{wod_id}", response_model=WODResponse)
async def update_wod(
    wod_id: int,
    wod_update: WODUpdate,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Update a WOD.
    """
    result = await db.execute(select(WOD).where(WOD.id == wod_id))
    wod = result.scalar_one_or_none()
    if not wod:
        raise HTTPException(status_code=404, detail="WOD not found")

    for field, value in wod_update.model_dump(exclude_unset=True).items():
        setattr(wod, field, value)

    await db.flush()

    # Reload with standards
    result = await db.execute(
        select(WOD)
        .where(WOD.id == wod_id)
        .options(selectinload(WOD.standards))
    )
    return result.scalar_one()


@router.delete("/wods/{wod_id}")
async def delete_wod(
    wod_id: int,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a WOD and related scores.
    """
    result = await db.execute(select(WOD).where(WOD.id == wod_id))
    wod = result.scalar_one_or_none()
    if not wod:
        raise HTTPException(status_code=404, detail="WOD not found")

    await db.delete(wod)
    return {"message": "WOD deleted successfully"}


# ============== WOD Standards ==============

@router.post("/wods/{wod_id}/standards", response_model=WODStandardResponse, status_code=status.HTTP_201_CREATED)
async def add_wod_standard(
    wod_id: int,
    standard: WODStandardCreate,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Add a standard to a WOD.
    """
    # Check WOD exists
    wod_result = await db.execute(select(WOD).where(WOD.id == wod_id))
    if not wod_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="WOD not found")

    # Check if standard for this division exists
    existing = await db.execute(
        select(WODStandard).where(
            WODStandard.wod_id == wod_id,
            WODStandard.division == standard.division
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Standard for division {standard.division} already exists"
        )

    new_standard = WODStandard(
        wod_id=wod_id,
        division=standard.division,
        rx_weight_kg=standard.rx_weight_kg,
        description_override=standard.description_override,
    )
    db.add(new_standard)
    await db.flush()
    await db.refresh(new_standard)
    return new_standard


@router.delete("/wods/{wod_id}/standards/{standard_id}")
async def delete_wod_standard(
    wod_id: int,
    standard_id: int,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a WOD standard.
    """
    result = await db.execute(
        select(WODStandard).where(
            WODStandard.id == standard_id,
            WODStandard.wod_id == wod_id
        )
    )
    standard = result.scalar_one_or_none()
    if not standard:
        raise HTTPException(status_code=404, detail="Standard not found")

    await db.delete(standard)
    return {"message": "Standard deleted successfully"}


# ============== Dashboard ==============

@router.get("/competitions/{competition_id}/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    competition_id: int,
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard statistics for a competition.
    """
    # Check competition exists
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    if not comp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Competition not found")

    # Total athletes
    athletes_result = await db.execute(
        select(func.count()).where(Athlete.competition_id == competition_id)
    )
    total_athletes = athletes_result.scalar()

    # Total WODs
    wods_result = await db.execute(
        select(func.count()).where(WOD.competition_id == competition_id)
    )
    total_wods = wods_result.scalar()

    # Get WOD IDs for this competition
    wod_ids_result = await db.execute(
        select(WOD.id).where(WOD.competition_id == competition_id)
    )
    wod_ids = [row[0] for row in wod_ids_result.all()]

    # Scores statistics
    scores_submitted = 0
    scores_pending = 0
    scores_verified = 0

    if wod_ids:
        # Total scores
        scores_result = await db.execute(
            select(func.count()).where(Score.wod_id.in_(wod_ids))
        )
        scores_submitted = scores_result.scalar()

        # Pending scores
        pending_result = await db.execute(
            select(func.count()).where(
                Score.wod_id.in_(wod_ids),
                Score.status == "pending"
            )
        )
        scores_pending = pending_result.scalar()

        # Verified scores
        verified_result = await db.execute(
            select(func.count()).where(
                Score.wod_id.in_(wod_ids),
                Score.status == "verified"
            )
        )
        scores_verified = verified_result.scalar()

    # Athletes by division
    division_result = await db.execute(
        select(Athlete.division, func.count())
        .where(Athlete.competition_id == competition_id)
        .group_by(Athlete.division)
    )
    divisions_summary = {row[0]: row[1] for row in division_result.all()}

    return DashboardStats(
        total_athletes=total_athletes,
        total_wods=total_wods,
        scores_submitted=scores_submitted,
        scores_pending=scores_pending,
        scores_verified=scores_verified,
        divisions_summary=divisions_summary,
    )


# ============== Scoring ==============

@router.post("/competitions/{competition_id}/recalculate")
async def recalculate_scores(
    competition_id: int,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Recalculate all rankings and points for a competition.
    Use this after importing scores or fixing data issues.
    """
    from scoring import recalculate_competition_scores

    # Check competition exists
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    if not comp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Competition not found")

    updated = await recalculate_competition_scores(db, competition_id)

    return {
        "message": f"Recalculated {updated} scores",
        "updated_count": updated
    }
