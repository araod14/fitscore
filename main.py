"""
FitScore - CrossFit Competition Management System
Main FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.cors import CORSMiddleware

from auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
)
from config import APP_NAME, APP_VERSION, DEBUG
from database import create_tables, get_db
from models import Competition, User
from routers import (
    admin_router,
    audit_router,
    auth_router,
    export_router,
    leaderboard_router,
    scores_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"Starting {APP_NAME} v{APP_VERSION}...")
    await create_tables()
    print("Database tables created/verified.")
    yield
    # Shutdown
    print(f"Shutting down {APP_NAME}...")


# Create FastAPI application
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Sistema de gestion de competencias CrossFit con puntuacion FitScore",
    lifespan=lifespan,
    docs_url="/api/docs" if DEBUG else None,
    redoc_url="/api/redoc" if DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")


# Template context processor
def get_template_context(request: Request, user: Optional[User] = None, **kwargs):
    """Build common template context."""
    return {
        "request": request,
        "user": user,
        "current_year": datetime.now().year,
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        **kwargs,
    }


# Include API routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(scores_router)
app.include_router(leaderboard_router)
app.include_router(audit_router)
app.include_router(export_router)


# ============== HTML Routes ==============


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Home page - redirect to appropriate dashboard."""
    if user:
        if user.role == "admin":
            return RedirectResponse(url="/admin", status_code=302)
        elif user.role == "judge":
            return RedirectResponse(url="/judge", status_code=302)
    return RedirectResponse(url="/leaderboard", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Login page."""
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        get_template_context(request),
    )


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Process login form submission."""
    user = await authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            get_template_context(request, error="Usuario o contrasena incorrectos"),
        )

    # Create token and set cookie
    token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=60 * 60 * 24,  # 24 hours
        samesite="lax",
    )
    return response


@app.get("/logout")
async def logout():
    """Logout and clear session."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response


# ============== Admin Routes ==============


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Admin dashboard."""
    if not user or user.role != "admin":
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "admin/dashboard.html",
        get_template_context(request, user=user),
    )


@app.get("/admin/competitions", response_class=HTMLResponse)
async def admin_competitions(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Competitions management page."""
    if not user or user.role != "admin":
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "admin/competitions.html",
        get_template_context(request, user=user),
    )


@app.get("/admin/competitions/{competition_id}", response_class=HTMLResponse)
async def admin_competition_detail(
    request: Request,
    competition_id: int,
    user: Optional[User] = Depends(get_current_user),
):
    """Competition detail page (redirects to athletes)."""
    if not user or user.role != "admin":
        return RedirectResponse(url="/login", status_code=302)

    return RedirectResponse(
        url=f"/admin/athletes?competition={competition_id}", status_code=302
    )


@app.get("/admin/athletes", response_class=HTMLResponse)
async def admin_athletes(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Athletes management page."""
    if not user or user.role != "admin":
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "admin/athletes.html",
        get_template_context(request, user=user),
    )


@app.get("/admin/wods", response_class=HTMLResponse)
async def admin_wods(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """WODs management page."""
    if not user or user.role != "admin":
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "admin/wods.html",
        get_template_context(request, user=user),
    )


@app.get("/admin/audit", response_class=HTMLResponse)
async def admin_audit(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Audit log page."""
    if not user or user.role != "admin":
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "admin/audit.html",
        get_template_context(request, user=user),
    )


# ============== Judge Routes ==============


@app.get("/judge", response_class=HTMLResponse)
async def judge_dashboard(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Judge dashboard."""
    if not user or user.role not in ["admin", "judge"]:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "judge/dashboard.html",
        get_template_context(request, user=user),
    )


@app.get("/judge/score/{competition_id}/{wod_id}", response_class=HTMLResponse)
async def judge_score_entry(
    request: Request,
    competition_id: int,
    wod_id: int,
    user: Optional[User] = Depends(get_current_user),
):
    """Score entry page for a specific WOD."""
    if not user or user.role not in ["admin", "judge"]:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "judge/score_entry.html",
        get_template_context(
            request,
            user=user,
            competition_id=competition_id,
            wod_id=wod_id,
        ),
    )


# ============== Public Routes ==============


@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_selector(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Leaderboard page - shows competition selector or redirects to active."""
    # Check for active competition
    result = await db.execute(select(Competition).where(Competition.is_active).limit(1))
    active_comp = result.scalar_one_or_none()

    if active_comp:
        return RedirectResponse(url=f"/leaderboard/{active_comp.id}", status_code=302)

    return templates.TemplateResponse(
        "public/leaderboard.html",
        get_template_context(request, user=user, competition_id=None, competition=None),
    )


@app.get("/leaderboard/{competition_id}", response_class=HTMLResponse)
async def leaderboard_competition(
    request: Request,
    competition_id: int,
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Leaderboard for a specific competition."""
    # Get competition
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()

    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")

    return templates.TemplateResponse(
        "public/leaderboard.html",
        get_template_context(
            request,
            user=user,
            competition_id=competition_id,
            competition=competition,
        ),
    )


# ============== Health Check ==============


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": APP_NAME,
        "version": APP_VERSION,
    }


@app.get("/api/status")
async def api_status():
    """API status endpoint."""
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============== Run Application ==============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
    )
