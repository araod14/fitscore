"""
Scores router for submitting and managing athlete scores.
"""

import json
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import get_current_admin, get_current_judge_or_admin
from config import AuditActions, ScoreStatus
from database import get_db
from models import WOD, Athlete, Score, ScoreAuditLog, User
from schemas import (
    ScoreBulkCreate,
    ScoreCreate,
    ScoreListResponse,
    ScoreResponse,
    ScoreUpdate,
)
from scoring import recalculate_wod_scores

router = APIRouter(prefix="/api/scores", tags=["Scores"])


async def create_audit_log(
    db: AsyncSession,
    score_id: int,
    action: str,
    user_id: int,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    ip_address: Optional[str] = None,
    reason: Optional[str] = None,
):
    """Create an audit log entry for a score change."""
    audit_log = ScoreAuditLog(
        score_id=score_id,
        action=action,
        old_value=json.dumps(old_value) if old_value else None,
        new_value=json.dumps(new_value) if new_value else None,
        user_id=user_id,
        ip_address=ip_address,
        reason=reason,
    )
    db.add(audit_log)


def score_to_dict(score: Score) -> dict:
    """Convert a score to a dict for audit logging."""
    return {
        "raw_result": score.raw_result,
        "tiebreak": score.tiebreak,
        "status": score.status,
        "notes": score.notes,
    }


@router.get("", response_model=ScoreListResponse)
async def list_scores(
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
    wod_id: Optional[int] = None,
    athlete_id: Optional[int] = None,
    competition_id: Optional[int] = None,
    division: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    List scores with optional filters.
    """
    query = select(Score).options(selectinload(Score.athlete), selectinload(Score.wod))

    if wod_id:
        query = query.where(Score.wod_id == wod_id)
    if athlete_id:
        query = query.where(Score.athlete_id == athlete_id)
    if status_filter:
        query = query.where(Score.status == status_filter)

    if competition_id:
        # Join with WOD to filter by competition
        query = query.join(WOD).where(WOD.competition_id == competition_id)

    if division:
        # Join with Athlete to filter by division
        if athlete_id is None:  # Only join if not already filtering by athlete
            query = query.join(Athlete, Score.athlete_id == Athlete.id).where(
                Athlete.division == division
            )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get items
    query = query.order_by(Score.submitted_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    scores = result.scalars().all()

    # Build response with additional info
    items = []
    for score in scores:
        items.append(
            ScoreResponse(
                id=score.id,
                athlete_id=score.athlete_id,
                wod_id=score.wod_id,
                raw_result=score.raw_result,
                tiebreak=score.tiebreak,
                rank=score.rank,
                points=score.points,
                status=score.status,
                notes=score.notes,
                judge_id=score.judge_id,
                submitted_at=score.submitted_at,
                verified_at=score.verified_at,
                verified_by=score.verified_by,
                athlete_name=score.athlete.name if score.athlete else None,
                athlete_bib=score.athlete.bib_number if score.athlete else None,
                wod_name=score.wod.name if score.wod else None,
            )
        )

    return ScoreListResponse(items=items, total=total)


@router.post("", response_model=ScoreResponse, status_code=status.HTTP_201_CREATED)
async def create_score(
    score_data: ScoreCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a new score for an athlete.
    """
    # Validate athlete exists
    athlete_result = await db.execute(
        select(Athlete).where(Athlete.id == score_data.athlete_id)
    )
    athlete = athlete_result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    # Validate WOD exists
    wod_result = await db.execute(select(WOD).where(WOD.id == score_data.wod_id))
    wod = wod_result.scalar_one_or_none()
    if not wod:
        raise HTTPException(status_code=404, detail="WOD not found")

    # Check athlete belongs to competition
    if athlete.competition_id != wod.competition_id:
        raise HTTPException(
            status_code=400, detail="Athlete does not belong to this competition"
        )

    # Check for existing score
    existing_result = await db.execute(
        select(Score).where(
            Score.athlete_id == score_data.athlete_id, Score.wod_id == score_data.wod_id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Score already exists for this athlete and WOD"
        )

    # Create score
    score = Score(
        athlete_id=score_data.athlete_id,
        wod_id=score_data.wod_id,
        raw_result=score_data.raw_result,
        tiebreak=score_data.tiebreak,
        notes=score_data.notes,
        judge_id=current_user.id,
        status=ScoreStatus.PENDING,
    )
    db.add(score)
    await db.flush()

    # Create audit log
    client_ip = request.client.host if request.client else None
    await create_audit_log(
        db,
        score.id,
        AuditActions.CREATE,
        current_user.id,
        new_value=score_to_dict(score),
        ip_address=client_ip,
    )

    # Recalculate rankings
    await recalculate_wod_scores(db, score_data.wod_id)

    await db.refresh(score)

    return ScoreResponse(
        id=score.id,
        athlete_id=score.athlete_id,
        wod_id=score.wod_id,
        raw_result=score.raw_result,
        tiebreak=score.tiebreak,
        rank=score.rank,
        points=score.points,
        status=score.status,
        notes=score.notes,
        judge_id=score.judge_id,
        submitted_at=score.submitted_at,
        verified_at=score.verified_at,
        verified_by=score.verified_by,
        athlete_name=athlete.name,
        athlete_bib=athlete.bib_number,
        wod_name=wod.name,
    )


@router.get("/{score_id}", response_model=ScoreResponse)
async def get_score(
    score_id: int,
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific score.
    """
    result = await db.execute(
        select(Score)
        .where(Score.id == score_id)
        .options(selectinload(Score.athlete), selectinload(Score.wod))
    )
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")

    return ScoreResponse(
        id=score.id,
        athlete_id=score.athlete_id,
        wod_id=score.wod_id,
        raw_result=score.raw_result,
        tiebreak=score.tiebreak,
        rank=score.rank,
        points=score.points,
        status=score.status,
        notes=score.notes,
        judge_id=score.judge_id,
        submitted_at=score.submitted_at,
        verified_at=score.verified_at,
        verified_by=score.verified_by,
        athlete_name=score.athlete.name if score.athlete else None,
        athlete_bib=score.athlete.bib_number if score.athlete else None,
        wod_name=score.wod.name if score.wod else None,
    )


@router.put("/{score_id}", response_model=ScoreResponse)
async def update_score(
    score_id: int,
    score_update: ScoreUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Update a score.
    """
    result = await db.execute(
        select(Score)
        .where(Score.id == score_id)
        .options(selectinload(Score.athlete), selectinload(Score.wod))
    )
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")

    # Store old values for audit
    old_values = score_to_dict(score)

    # Update fields
    if score_update.raw_result is not None:
        score.raw_result = score_update.raw_result
    if score_update.tiebreak is not None:
        score.tiebreak = score_update.tiebreak
    if score_update.notes is not None:
        score.notes = score_update.notes
    if score_update.status is not None:
        score.status = score_update.status
        if score_update.status == ScoreStatus.VERIFIED:
            score.verified_at = datetime.utcnow()
            score.verified_by = current_user.id

    await db.flush()

    # Create audit log
    client_ip = request.client.host if request.client else None
    await create_audit_log(
        db,
        score.id,
        AuditActions.UPDATE,
        current_user.id,
        old_value=old_values,
        new_value=score_to_dict(score),
        ip_address=client_ip,
        reason=score_update.reason,
    )

    # Recalculate rankings
    await recalculate_wod_scores(db, score.wod_id)

    await db.refresh(score)

    return ScoreResponse(
        id=score.id,
        athlete_id=score.athlete_id,
        wod_id=score.wod_id,
        raw_result=score.raw_result,
        tiebreak=score.tiebreak,
        rank=score.rank,
        points=score.points,
        status=score.status,
        notes=score.notes,
        judge_id=score.judge_id,
        submitted_at=score.submitted_at,
        verified_at=score.verified_at,
        verified_by=score.verified_by,
        athlete_name=score.athlete.name if score.athlete else None,
        athlete_bib=score.athlete.bib_number if score.athlete else None,
        wod_name=score.wod.name if score.wod else None,
    )


@router.delete("/{score_id}")
async def delete_score(
    score_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a score (admin only).
    """
    result = await db.execute(select(Score).where(Score.id == score_id))
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")

    wod_id = score.wod_id

    # Create audit log before deletion
    client_ip = request.client.host if request.client else None
    await create_audit_log(
        db,
        score.id,
        AuditActions.DELETE,
        current_user.id,
        old_value=score_to_dict(score),
        ip_address=client_ip,
    )

    await db.delete(score)

    # Recalculate rankings
    await recalculate_wod_scores(db, wod_id)

    return {"message": "Score deleted successfully"}


@router.post("/{score_id}/verify", response_model=ScoreResponse)
async def verify_score(
    score_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a score (admin only).
    """
    result = await db.execute(
        select(Score)
        .where(Score.id == score_id)
        .options(selectinload(Score.athlete), selectinload(Score.wod))
    )
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")

    old_values = score_to_dict(score)

    score.status = ScoreStatus.VERIFIED
    score.verified_at = datetime.utcnow()
    score.verified_by = current_user.id

    await db.flush()

    # Create audit log
    client_ip = request.client.host if request.client else None
    await create_audit_log(
        db,
        score.id,
        AuditActions.VERIFY,
        current_user.id,
        old_value=old_values,
        new_value=score_to_dict(score),
        ip_address=client_ip,
    )

    await db.refresh(score)

    return ScoreResponse(
        id=score.id,
        athlete_id=score.athlete_id,
        wod_id=score.wod_id,
        raw_result=score.raw_result,
        tiebreak=score.tiebreak,
        rank=score.rank,
        points=score.points,
        status=score.status,
        notes=score.notes,
        judge_id=score.judge_id,
        submitted_at=score.submitted_at,
        verified_at=score.verified_at,
        verified_by=score.verified_by,
        athlete_name=score.athlete.name if score.athlete else None,
        athlete_bib=score.athlete.bib_number if score.athlete else None,
        wod_name=score.wod.name if score.wod else None,
    )


@router.post(
    "/bulk", response_model=List[ScoreResponse], status_code=status.HTTP_201_CREATED
)
async def bulk_create_scores(
    bulk_data: ScoreBulkCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk create scores.
    """
    created_scores = []
    wods_to_recalculate = set()
    client_ip = request.client.host if request.client else None

    for score_data in bulk_data.scores:
        # Validate athlete and WOD exist
        athlete_result = await db.execute(
            select(Athlete).where(Athlete.id == score_data.athlete_id)
        )
        athlete = athlete_result.scalar_one_or_none()
        if not athlete:
            continue

        wod_result = await db.execute(select(WOD).where(WOD.id == score_data.wod_id))
        wod = wod_result.scalar_one_or_none()
        if not wod:
            continue

        # Check for existing
        existing = await db.execute(
            select(Score).where(
                Score.athlete_id == score_data.athlete_id,
                Score.wod_id == score_data.wod_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        score = Score(
            athlete_id=score_data.athlete_id,
            wod_id=score_data.wod_id,
            raw_result=score_data.raw_result,
            tiebreak=score_data.tiebreak,
            notes=score_data.notes,
            judge_id=current_user.id,
            status=ScoreStatus.PENDING,
        )
        db.add(score)
        await db.flush()

        # Audit log
        await create_audit_log(
            db,
            score.id,
            AuditActions.CREATE,
            current_user.id,
            new_value=score_to_dict(score),
            ip_address=client_ip,
        )

        wods_to_recalculate.add(score_data.wod_id)

        created_scores.append(
            ScoreResponse(
                id=score.id,
                athlete_id=score.athlete_id,
                wod_id=score.wod_id,
                raw_result=score.raw_result,
                tiebreak=score.tiebreak,
                rank=score.rank,
                points=score.points,
                status=score.status,
                notes=score.notes,
                judge_id=score.judge_id,
                submitted_at=score.submitted_at,
                verified_at=score.verified_at,
                verified_by=score.verified_by,
                athlete_name=athlete.name,
                athlete_bib=athlete.bib_number,
                wod_name=wod.name,
            )
        )

    # Recalculate all affected WODs
    for wod_id in wods_to_recalculate:
        await recalculate_wod_scores(db, wod_id)

    return created_scores


@router.get("/search/athlete")
async def search_athlete_for_scoring(
    current_user: Annotated[User, Depends(get_current_judge_or_admin)],
    db: AsyncSession = Depends(get_db),
    competition_id: int = Query(...),
    q: str = Query(..., min_length=1),
):
    """
    Search for an athlete by name or bib number for scoring.
    """
    query = (
        select(Athlete)
        .where(
            Athlete.competition_id == competition_id,
            (Athlete.name.ilike(f"%{q}%")) | (Athlete.bib_number.ilike(f"%{q}%")),
        )
        .limit(10)
    )

    result = await db.execute(query)
    athletes = result.scalars().all()

    return [
        {
            "id": a.id,
            "name": a.name,
            "bib_number": a.bib_number,
            "division": a.division,
            "box": a.box,
        }
        for a in athletes
    ]
