"""
Audit router for viewing score change history.
"""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import get_current_admin
from database import get_db
from models import WOD, Score, ScoreAuditLog, User
from schemas import AuditLogListResponse, AuditLogResponse

router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
    score_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    competition_id: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    List audit logs with filters (admin only).
    """
    query = select(ScoreAuditLog).options(
        selectinload(ScoreAuditLog.user),
        selectinload(ScoreAuditLog.score).selectinload(Score.athlete),
        selectinload(ScoreAuditLog.score).selectinload(Score.wod),
    )

    # Apply filters
    if score_id:
        query = query.where(ScoreAuditLog.score_id == score_id)
    if user_id:
        query = query.where(ScoreAuditLog.user_id == user_id)
    if action:
        query = query.where(ScoreAuditLog.action == action)
    if from_date:
        query = query.where(ScoreAuditLog.timestamp >= from_date)
    if to_date:
        query = query.where(ScoreAuditLog.timestamp <= to_date)

    # Filter by competition (requires join through Score -> WOD)
    if competition_id:
        query = query.join(Score).join(WOD).where(WOD.competition_id == competition_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get items
    query = query.order_by(ScoreAuditLog.timestamp.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    # Build response
    items = []
    for log in logs:
        items.append(
            AuditLogResponse(
                id=log.id,
                score_id=log.score_id,
                action=log.action,
                old_value=log.old_value,
                new_value=log.new_value,
                user_id=log.user_id,
                username=log.user.username if log.user else None,
                timestamp=log.timestamp,
                ip_address=log.ip_address,
                reason=log.reason,
                athlete_name=(
                    log.score.athlete.name if log.score and log.score.athlete else None
                ),
                wod_name=log.score.wod.name if log.score and log.score.wod else None,
            )
        )

    return AuditLogListResponse(items=items, total=total)


@router.get("/score/{score_id}", response_model=AuditLogListResponse)
async def get_score_audit_history(
    score_id: int,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete audit history for a specific score.
    """
    # Check score exists
    score_result = await db.execute(
        select(Score)
        .where(Score.id == score_id)
        .options(selectinload(Score.athlete), selectinload(Score.wod))
    )
    score = score_result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")

    # Get all audit logs for this score
    result = await db.execute(
        select(ScoreAuditLog)
        .where(ScoreAuditLog.score_id == score_id)
        .options(selectinload(ScoreAuditLog.user))
        .order_by(ScoreAuditLog.timestamp.desc())
    )
    logs = result.scalars().all()

    items = []
    for log in logs:
        items.append(
            AuditLogResponse(
                id=log.id,
                score_id=log.score_id,
                action=log.action,
                old_value=log.old_value,
                new_value=log.new_value,
                user_id=log.user_id,
                username=log.user.username if log.user else None,
                timestamp=log.timestamp,
                ip_address=log.ip_address,
                reason=log.reason,
                athlete_name=score.athlete.name if score.athlete else None,
                wod_name=score.wod.name if score.wod else None,
            )
        )

    return AuditLogListResponse(items=items, total=len(items))


@router.get("/user/{user_id}", response_model=AuditLogListResponse)
async def get_user_audit_history(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get audit history for actions by a specific user.
    """
    # Check user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Count total
    count_result = await db.execute(
        select(func.count()).where(ScoreAuditLog.user_id == user_id)
    )
    total = count_result.scalar()

    # Get logs
    result = await db.execute(
        select(ScoreAuditLog)
        .where(ScoreAuditLog.user_id == user_id)
        .options(
            selectinload(ScoreAuditLog.user),
            selectinload(ScoreAuditLog.score).selectinload(Score.athlete),
            selectinload(ScoreAuditLog.score).selectinload(Score.wod),
        )
        .order_by(ScoreAuditLog.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()

    items = []
    for log in logs:
        items.append(
            AuditLogResponse(
                id=log.id,
                score_id=log.score_id,
                action=log.action,
                old_value=log.old_value,
                new_value=log.new_value,
                user_id=log.user_id,
                username=user.username,
                timestamp=log.timestamp,
                ip_address=log.ip_address,
                reason=log.reason,
                athlete_name=(
                    log.score.athlete.name if log.score and log.score.athlete else None
                ),
                wod_name=log.score.wod.name if log.score and log.score.wod else None,
            )
        )

    return AuditLogListResponse(items=items, total=total)


@router.get("/stats")
async def get_audit_stats(
    current_user: Annotated[User, Depends(get_current_admin)],
    db: AsyncSession = Depends(get_db),
    competition_id: Optional[int] = None,
):
    """
    Get audit statistics for a competition or overall.
    """
    base_query = select(ScoreAuditLog)

    if competition_id:
        base_query = (
            base_query.join(Score).join(WOD).where(WOD.competition_id == competition_id)
        )

    # Total actions
    total_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = total_result.scalar()

    # Actions by type
    actions_query = select(ScoreAuditLog.action, func.count()).group_by(
        ScoreAuditLog.action
    )
    if competition_id:
        actions_query = (
            select(ScoreAuditLog.action, func.count())
            .join(Score)
            .join(WOD)
            .where(WOD.competition_id == competition_id)
            .group_by(ScoreAuditLog.action)
        )
    actions_result = await db.execute(actions_query)
    actions_by_type = {row[0]: row[1] for row in actions_result.all()}

    # Actions by user (top 10)
    users_query = select(User.username, func.count()).join(
        ScoreAuditLog, ScoreAuditLog.user_id == User.id
    )
    if competition_id:
        users_query = (
            select(User.username, func.count())
            .join(ScoreAuditLog, ScoreAuditLog.user_id == User.id)
            .join(Score, ScoreAuditLog.score_id == Score.id)
            .join(WOD, Score.wod_id == WOD.id)
            .where(WOD.competition_id == competition_id)
        )
    users_query = (
        users_query.group_by(User.username).order_by(func.count().desc()).limit(10)
    )
    users_result = await db.execute(users_query)
    actions_by_user = {row[0]: row[1] for row in users_result.all()}

    return {
        "total_actions": total,
        "actions_by_type": actions_by_type,
        "top_users": actions_by_user,
    }
