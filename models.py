"""
SQLAlchemy ORM Models for FitScore application.
"""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config import Roles, ScoreStatus
from database import Base


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default=Roles.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=datetime.utcnow
    )

    # Relationships
    competitions_created: Mapped[List["Competition"]] = relationship(
        "Competition", back_populates="creator", foreign_keys="Competition.created_by"
    )
    scores_submitted: Mapped[List["Score"]] = relationship(
        "Score", back_populates="judge", foreign_keys="Score.judge_id"
    )
    scores_verified: Mapped[List["Score"]] = relationship(
        "Score", back_populates="verifier", foreign_keys="Score.verified_by"
    )
    audit_logs: Mapped[List["ScoreAuditLog"]] = relationship(
        "ScoreAuditLog", back_populates="user"
    )

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Competition(Base):
    """Competition/Event model."""

    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=datetime.utcnow
    )
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User", back_populates="competitions_created"
    )
    athletes: Mapped[List["Athlete"]] = relationship(
        "Athlete", back_populates="competition", cascade="all, delete-orphan"
    )
    wods: Mapped[List["WOD"]] = relationship(
        "WOD", back_populates="competition", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Competition {self.name}>"


class Athlete(Base):
    """Athlete/Competitor model."""

    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    division: Mapped[str] = mapped_column(String(50), nullable=False)
    box: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # CrossFit gym/box
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    bib_number: Mapped[str] = mapped_column(String(20), nullable=False)  # Dorsal number
    competition_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitions.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=datetime.utcnow
    )

    # Relationships
    competition: Mapped["Competition"] = relationship(
        "Competition", back_populates="athletes"
    )
    scores: Mapped[List["Score"]] = relationship(
        "Score", back_populates="athlete", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "bib_number", "competition_id", name="uq_athlete_bib_competition"
        ),
        Index("ix_athlete_competition_division", "competition_id", "division"),
    )

    @property
    def age(self) -> Optional[int]:
        """Calculate athlete's age."""
        if not self.birth_date:
            return None
        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )

    def __repr__(self):
        return f"<Athlete {self.name} ({self.bib_number})>"


class WOD(Base):
    """Workout of the Day model."""

    __tablename__ = "wods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    wod_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # time, amrap, load, reps, etc.
    time_cap: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # in seconds
    order_in_competition: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    competition_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitions.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=datetime.utcnow
    )

    # Relationships
    competition: Mapped["Competition"] = relationship(
        "Competition", back_populates="wods"
    )
    standards: Mapped[List["WODStandard"]] = relationship(
        "WODStandard", back_populates="wod", cascade="all, delete-orphan"
    )
    scores: Mapped[List["Score"]] = relationship(
        "Score", back_populates="wod", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        Index("ix_wod_competition_order", "competition_id", "order_in_competition"),
    )

    @property
    def time_cap_formatted(self) -> Optional[str]:
        """Return time cap in mm:ss format."""
        if not self.time_cap:
            return None
        minutes = self.time_cap // 60
        seconds = self.time_cap % 60
        return f"{minutes}:{seconds:02d}"

    def __repr__(self):
        return f"<WOD {self.name} ({self.wod_type})>"


class WODStandard(Base):
    """WOD standards per division (weights, movements, etc.)."""

    __tablename__ = "wod_standards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wod_id: Mapped[int] = mapped_column(Integer, ForeignKey("wods.id"), nullable=False)
    division: Mapped[str] = mapped_column(String(50), nullable=False)
    rx_weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description_override: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    wod: Mapped["WOD"] = relationship("WOD", back_populates="standards")

    # Constraints
    __table_args__ = (
        UniqueConstraint("wod_id", "division", name="uq_wod_standard_division"),
    )

    def __repr__(self):
        return f"<WODStandard {self.division} - {self.rx_weight_kg}kg>"


class Score(Base):
    """Score/Result for an athlete in a WOD."""

    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("athletes.id"), nullable=False
    )
    wod_id: Mapped[int] = mapped_column(Integer, ForeignKey("wods.id"), nullable=False)

    # Raw result - interpretation depends on WOD type
    # For time: seconds (e.g., 305 = 5:05)
    # For amrap/reps/calories: integer count
    # For load: kg (can be float)
    raw_result: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Tiebreak value (for time-capped AMRAPs, etc.)
    tiebreak: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Calculated rank within division for this WOD
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Points earned for this WOD (FitScore system)
    points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status and verification
    status: Mapped[str] = mapped_column(
        String(20), default=ScoreStatus.PENDING, nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit fields
    judge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verified_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    # Relationships
    athlete: Mapped["Athlete"] = relationship("Athlete", back_populates="scores")
    wod: Mapped["WOD"] = relationship("WOD", back_populates="scores")
    judge: Mapped["User"] = relationship(
        "User", back_populates="scores_submitted", foreign_keys=[judge_id]
    )
    verifier: Mapped[Optional["User"]] = relationship(
        "User", back_populates="scores_verified", foreign_keys=[verified_by]
    )
    audit_logs: Mapped[List["ScoreAuditLog"]] = relationship(
        "ScoreAuditLog", back_populates="score", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("athlete_id", "wod_id", name="uq_score_athlete_wod"),
        Index("ix_score_wod_rank", "wod_id", "rank"),
    )

    @property
    def result_formatted(self) -> str:
        """Format result based on WOD type."""
        if self.raw_result is None:
            return "-"
        return str(self.raw_result)

    def __repr__(self):
        return f"<Score A:{self.athlete_id} W:{self.wod_id} R:{self.raw_result}>"


class ScoreAuditLog(Base):
    """Audit log for score changes."""

    __tablename__ = "score_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    score_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scores.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # create, update, delete, verify
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    score: Mapped["Score"] = relationship("Score", back_populates="audit_logs")
    user: Mapped["User"] = relationship("User", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index("ix_audit_score_timestamp", "score_id", "timestamp"),
        Index("ix_audit_user_timestamp", "user_id", "timestamp"),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} Score:{self.score_id} User:{self.user_id}>"
