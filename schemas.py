"""
Pydantic schemas for request/response validation.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from config import DIVISIONS, GENDERS, ROLES, SCORE_STATUSES, WOD_TYPES

# ============== User Schemas ==============


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    role: str = Field(default="viewer")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ROLES:
            raise ValueError(f"Role must be one of: {ROLES}")
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v is not None and v not in ROLES:
            raise ValueError(f"Role must be one of: {ROLES}")
        return v


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    username: str
    role: str


# ============== Competition Schemas ==============


class CompetitionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    date: date
    location: Optional[str] = Field(None, max_length=200)


class CompetitionCreate(CompetitionBase):
    pass


class CompetitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    date: Optional[date] = None
    location: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class CompetitionResponse(CompetitionBase):
    id: int
    is_active: bool
    created_at: datetime
    created_by: int
    athlete_count: Optional[int] = 0
    wod_count: Optional[int] = 0

    class Config:
        from_attributes = True


class CompetitionListResponse(BaseModel):
    items: List[CompetitionResponse]
    total: int


# ============== Athlete Schemas ==============


class AthleteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    gender: str
    birth_date: Optional[date] = None
    category: Optional[str] = Field(None, max_length=50)
    division: str
    box: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=30)
    bib_number: str = Field(..., min_length=1, max_length=20)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        if v not in GENDERS:
            raise ValueError(f"Gender must be one of: {GENDERS}")
        return v

    @field_validator("division")
    @classmethod
    def validate_division(cls, v):
        if v not in DIVISIONS:
            raise ValueError(f"Division must be one of: {DIVISIONS}")
        return v


class AthleteCreate(AthleteBase):
    competition_id: int


class AthleteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    category: Optional[str] = Field(None, max_length=50)
    division: Optional[str] = None
    box: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=30)
    bib_number: Optional[str] = Field(None, min_length=1, max_length=20)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        if v is not None and v not in GENDERS:
            raise ValueError(f"Gender must be one of: {GENDERS}")
        return v

    @field_validator("division")
    @classmethod
    def validate_division(cls, v):
        if v is not None and v not in DIVISIONS:
            raise ValueError(f"Division must be one of: {DIVISIONS}")
        return v


class AthleteResponse(AthleteBase):
    id: int
    competition_id: int
    created_at: datetime
    age: Optional[int] = None
    total_points: Optional[float] = None
    rank_in_division: Optional[int] = None

    class Config:
        from_attributes = True


class AthleteListResponse(BaseModel):
    items: List[AthleteResponse]
    total: int


class AthleteImportRow(BaseModel):
    name: str
    gender: str
    birth_date: Optional[str] = None
    division: str
    box: Optional[str] = None
    bib_number: str


class AthleteImportResult(BaseModel):
    success_count: int
    error_count: int
    errors: List[str]


# ============== WOD Schemas ==============


class WODStandardBase(BaseModel):
    division: str
    rx_weight_kg: Optional[float] = None
    description_override: Optional[str] = None

    @field_validator("division")
    @classmethod
    def validate_division(cls, v):
        if v not in DIVISIONS:
            raise ValueError(f"Division must be one of: {DIVISIONS}")
        return v


class WODStandardCreate(WODStandardBase):
    pass


class WODStandardResponse(WODStandardBase):
    id: int
    wod_id: int

    class Config:
        from_attributes = True


class WODBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    wod_type: str
    time_cap: Optional[int] = Field(None, ge=0)  # seconds
    order_in_competition: int = Field(default=1, ge=1)

    @field_validator("wod_type")
    @classmethod
    def validate_wod_type(cls, v):
        if v not in WOD_TYPES:
            raise ValueError(f"WOD type must be one of: {WOD_TYPES}")
        return v


class WODCreate(WODBase):
    competition_id: int
    standards: Optional[List[WODStandardCreate]] = None


class WODUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    wod_type: Optional[str] = None
    time_cap: Optional[int] = Field(None, ge=0)
    order_in_competition: Optional[int] = Field(None, ge=1)

    @field_validator("wod_type")
    @classmethod
    def validate_wod_type(cls, v):
        if v is not None and v not in WOD_TYPES:
            raise ValueError(f"WOD type must be one of: {WOD_TYPES}")
        return v


class WODResponse(WODBase):
    id: int
    competition_id: int
    created_at: datetime
    time_cap_formatted: Optional[str] = None
    standards: List[WODStandardResponse] = []

    class Config:
        from_attributes = True


class WODListResponse(BaseModel):
    items: List[WODResponse]
    total: int


# ============== Score Schemas ==============


class ScoreBase(BaseModel):
    raw_result: Optional[float] = None
    result_type: str = Field(default="RX")
    tiebreak: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("result_type")
    @classmethod
    def validate_result_type(cls, v):
        valid_types = ["RX", "Scaled", "DNF", "DNS"]
        if v not in valid_types:
            raise ValueError(f"Result type must be one of: {valid_types}")
        return v


class ScoreCreate(ScoreBase):
    athlete_id: int
    wod_id: int


class ScoreUpdate(BaseModel):
    raw_result: Optional[float] = None
    result_type: Optional[str] = None
    tiebreak: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None  # Reason for the update (for audit)

    @field_validator("result_type")
    @classmethod
    def validate_result_type(cls, v):
        if v is not None:
            valid_types = ["RX", "Scaled", "DNF", "DNS"]
            if v not in valid_types:
                raise ValueError(f"Result type must be one of: {valid_types}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in SCORE_STATUSES:
            raise ValueError(f"Status must be one of: {SCORE_STATUSES}")
        return v


class ScoreResponse(ScoreBase):
    id: int
    athlete_id: int
    wod_id: int
    rank: Optional[int] = None
    points: Optional[float] = None
    status: str
    judge_id: int
    submitted_at: datetime
    verified_at: Optional[datetime] = None
    verified_by: Optional[int] = None
    athlete_name: Optional[str] = None
    athlete_bib: Optional[str] = None
    wod_name: Optional[str] = None

    class Config:
        from_attributes = True


class ScoreListResponse(BaseModel):
    items: List[ScoreResponse]
    total: int


class ScoreBulkCreate(BaseModel):
    scores: List[ScoreCreate]


# ============== Leaderboard Schemas ==============


class LeaderboardEntry(BaseModel):
    rank: int
    athlete_id: int
    athlete_name: str
    bib_number: str
    box: Optional[str] = None
    division: str
    total_points: float
    wod_scores: List[dict]  # List of {wod_id, rank, points, result}


class DivisionLeaderboard(BaseModel):
    division: str
    entries: List[LeaderboardEntry]


class CompetitionLeaderboard(BaseModel):
    competition_id: int
    competition_name: str
    updated_at: datetime
    divisions: List[DivisionLeaderboard]


# ============== Audit Schemas ==============


class AuditLogResponse(BaseModel):
    id: int
    score_id: int
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    user_id: int
    username: Optional[str] = None
    timestamp: datetime
    ip_address: Optional[str] = None
    reason: Optional[str] = None
    athlete_name: Optional[str] = None
    wod_name: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int


class AuditLogFilter(BaseModel):
    score_id: Optional[int] = None
    user_id: Optional[int] = None
    action: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    athlete_id: Optional[int] = None
    wod_id: Optional[int] = None


# ============== Export Schemas ==============


class ExportRequest(BaseModel):
    competition_id: int
    divisions: Optional[List[str]] = None  # None = all divisions
    format: str = Field(default="excel")  # excel, pdf, csv

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        valid_formats = ["excel", "pdf", "csv"]
        if v not in valid_formats:
            raise ValueError(f"Format must be one of: {valid_formats}")
        return v


# ============== Dashboard Schemas ==============


class DashboardStats(BaseModel):
    total_athletes: int
    total_wods: int
    scores_submitted: int
    scores_pending: int
    scores_verified: int
    divisions_summary: dict  # {division: athlete_count}


class JudgeDashboard(BaseModel):
    pending_scores: int
    recent_scores: List[ScoreResponse]
    assigned_wods: List[WODResponse]


# ============== Time Conversion Helpers ==============


def seconds_to_time_str(seconds: Optional[float]) -> str:
    """Convert seconds to mm:ss format."""
    if seconds is None:
        return "-"
    total_seconds = int(seconds)
    minutes = total_seconds // 60
    secs = total_seconds % 60
    return f"{minutes}:{secs:02d}"


def time_str_to_seconds(time_str: str) -> Optional[float]:
    """Convert mm:ss format to seconds."""
    if not time_str or time_str == "-":
        return None
    try:
        parts = time_str.split(":")
        if len(parts) == 2:
            minutes, seconds = int(parts[0]), int(parts[1])
            return minutes * 60 + seconds
        return float(time_str)
    except (ValueError, AttributeError):
        return None
