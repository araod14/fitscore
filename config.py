"""
Podium Configuration - Constants and settings for CrossFit competition management.
"""

import os

# Application Settings
APP_NAME = "Podium"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./podium.db")
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC", "sqlite:///./podium.db")

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY", "podium-secret-key-change-in-production-2025")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


# User Roles
class Roles:
    ADMIN = "admin"
    JUDGE = "judge"
    VIEWER = "viewer"


ROLES = [Roles.ADMIN, Roles.JUDGE, Roles.VIEWER]

# Team division sentinel (used for team-mode competitions)
TEAM_DIVISION = "Equipos"

# Divisions
DIVISIONS = [
    "Libre Masculino",
    "Libre Femenino",
    "Scaled Masculino",
    "Scaled Femenino",
    "Master +40 Masculino",
    "Master +40 Femenino",
    "Novato Masculino",
    "Novato Femenino",
]

# Categories (age-based)
CATEGORIES = [
    "Elite",
    "Intermediate",
    "Scaled",
    "Master 40-44",
    "Master 45-49",
    "Master 50-54",
    "Master 55-59",
    "Master 60+",
    "Teen 14-15",
    "Teen 16-17",
]

# Genders
GENDERS = ["Masculino", "Femenino"]


# WOD Types
class WODTypes:
    TIME = "time"  # Lower is better (mm:ss format)
    AMRAP = "amrap"  # Higher reps is better
    LOAD = "load"  # Higher weight is better (kg)
    REPS = "reps"  # Higher is better
    CALORIES = "calories"  # Higher is better
    DISTANCE = "distance"  # Higher is better (meters)


WOD_TYPES = [
    WODTypes.TIME,
    WODTypes.AMRAP,
    WODTypes.LOAD,
    WODTypes.REPS,
    WODTypes.CALORIES,
    WODTypes.DISTANCE,
]

# WOD Type Labels (for UI)
WOD_TYPE_LABELS = {
    WODTypes.TIME: "For Time",
    WODTypes.AMRAP: "AMRAP (Reps)",
    WODTypes.LOAD: "Max Load (kg)",
    WODTypes.REPS: "Max Reps",
    WODTypes.CALORIES: "Calories",
    WODTypes.DISTANCE: "Distance (m)",
}


# Score Status
class ScoreStatus:
    PENDING = "pending"
    VERIFIED = "verified"
    DISPUTED = "disputed"


SCORE_STATUSES = [ScoreStatus.PENDING, ScoreStatus.VERIFIED, ScoreStatus.DISPUTED]


# Audit Actions
class AuditActions:
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VERIFY = "verify"


AUDIT_ACTIONS = [
    AuditActions.CREATE,
    AuditActions.UPDATE,
    AuditActions.DELETE,
    AuditActions.VERIFY,
]

# Pagination
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# Leaderboard auto-refresh interval (seconds)
LEADERBOARD_REFRESH_INTERVAL = 30

# Age validation thresholds
MASTER_MIN_AGE = 40
TEEN_MAX_AGE = 17

# Time cap default (minutes)
DEFAULT_TIME_CAP = 20
