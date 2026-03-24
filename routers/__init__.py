"""
API Routers for FitScore application.
"""

from .admin import router as admin_router
from .audit import router as audit_router
from .auth import router as auth_router
from .export import router as export_router
from .leaderboard import router as leaderboard_router
from .scores import router as scores_router

__all__ = [
    "auth_router",
    "admin_router",
    "scores_router",
    "leaderboard_router",
    "audit_router",
    "export_router",
]
