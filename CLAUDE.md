# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make install        # Create venv and install dependencies (local dev)
make seed           # Install + populate with test data
make dev            # Run development server (port 8000, hot reload)
make prod           # Run production server (gunicorn)
make migrate        # Run Alembic migrations
make reset          # Full reset: clean + install + seed

# Docker commands (for VPS deployment)
make docker-build   # Build Docker image
make docker-up      # Start containers
make docker-down    # Stop containers
make docker-deploy  # Deploy: git pull + rebuild + restart
make docker-logs    # View container logs
make docker-shell   # Access container shell
```

Direct equivalents:
```bash
uvicorn main:app --reload          # Dev server
alembic upgrade head               # Migrations
pytest                             # Tests
```

Test credentials after `make seed`: `admin/admin123`, `judge1/judge123`, `viewer/viewer123`
API docs: `http://localhost:8000/api/docs`

## Architecture

**FastAPI + SQLAlchemy async backend** with Jinja2 templates, no separate frontend build step.

### Request flow
1. `main.py` — mounts API routers and HTML view routes (login, admin, judge, public)
2. `auth.py` — JWT via cookies; role-based dependency injection gates endpoints
3. `routers/` — route handlers call into `scoring/fitscore.py` after score writes
4. `scoring/fitscore.py` — recalculates rankings and FitScore points for the whole competition on each score change

### Key modules
| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy ORM: Competition, Athlete, WOD, WODStandard, Score, ScoreAuditLog, User |
| `schemas.py` | Pydantic request/response validation |
| `config.py` | Constants: DIVISIONS (10 categories), WOD_TYPES, token expiry |
| `routers/admin.py` | CRUD for competitions, athletes, WODs; CSV bulk import |
| `routers/scores.py` | Score submission and verification |
| `routers/export.py` | PDF (reportlab), Excel (openpyxl), CSV generation |
| `routers/audit.py` | Score change history queries |

### Scoring algorithm (`scoring/fitscore.py`)
- WOD types: `time`, `amrap`, `load`, `reps`, `calories`, `distance`
- Rank athletes per WOD per division; award points (1st = N, last = 1); sum across WODs = FitScore
- DNF/DNS handled explicitly; ties share rank and points
- Called synchronously after every score write — no background jobs

### Data model relationships
```
Competition → Athletes (many), WODs (many)
WOD → WODStandards (per division), Scores
Athlete → Scores (one per WOD)
Score → ScoreAuditLog (every change logged with user, IP, old/new values)
```

### Database
SQLite with `aiosqlite`; async sessions via `database.py`. Migrations in `alembic/`. The `fitscore.db` file is local and excluded from git.

### Frontend
Jinja2 templates with TailwindCSS (CDN) and Alpine.js — no build step needed.

## Docker Deployment

### Initial Setup (one time)

1. **SSH into VPS and clone repo:**
   ```bash
   ssh user@your-vps-ip
   cd /path/to/projects  # Your Docker projects directory
   git clone https://github.com/yourusername/fitscore.git
   cd fitscore
   ```

2. **Install Docker & Docker Compose** (if not already installed):
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose
   sudo usermod -aG docker $USER  # Add user to docker group
   newgrp docker  # Activate group changes
   ```

3. **Create `.env` file with production config:**
   ```bash
   cat > .env << 'EOF'
   SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
   DEBUG=False
   EOF
   chmod 600 .env
   ```

4. **Build and start containers:**
   ```bash
   make docker-build
   make docker-up
   ```

5. **Run migrations:**
   ```bash
   docker-compose exec -T app alembic upgrade head
   ```

   App is now available at `http://your-vps-ip`

### Configuration Files

- **`docker-compose.yml`** — Defines app and nginx services, volumes, networks
- **`nginx.conf`** — Reverse proxy configuration (HTTP/HTTPS)
- **`Dockerfile`** — Python 3.11-slim with gunicorn and FastAPI
- **`.env`** — Environment variables (not in git, create per deployment)

### SSL/HTTPS Setup

1. **Copy SSL certificates to `/ssl` directory:**
   ```bash
   mkdir -p ssl
   cp your-cert.pem ssl/cert.pem
   cp your-key.pem ssl/key.pem
   ```

2. **Uncomment HTTPS section in `nginx.conf` and update domain:**
   ```bash
   sed -i 's/# server {/server {/' nginx.conf
   # Then manually edit server_name and paths in nginx.conf
   ```

3. **Restart nginx:**
   ```bash
   make docker-down
   make docker-up
   ```

### Ongoing Deployments

After each code change, deploy with one command:
```bash
make docker-deploy  # git pull + rebuild + restart + migrations
```

Or step-by-step:
```bash
git pull origin main
make docker-build
make docker-up
docker-compose exec -T app alembic upgrade head
```

### Monitoring & Debugging

```bash
make docker-logs           # View live logs
make docker-shell          # Access app container shell
docker-compose ps          # List running containers
docker-compose down        # Stop all containers
```

### Useful Docker Commands

```bash
# View logs for specific service
docker-compose logs app
docker-compose logs nginx

# Restart a service
docker-compose restart app

# Rebuild without cache
docker-compose build --no-cache

# Remove volumes and data (careful!)
docker-compose down -v
```
