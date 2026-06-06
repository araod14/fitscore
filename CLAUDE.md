# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make install     # Create venv and install dependencies
make seed        # Install + populate with test data
make dev         # Run development server (port 8000, hot reload)
make prod        # Run production server (gunicorn)
make migrate     # Run Alembic migrations
make reset       # Full reset: clean + install + seed
make deploy      # Deploy to VPS: git pull + install + migrate + restart
make setup-vps   # Initial VPS setup (run once)
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

## VPS Deployment

### Initial Setup (one time)

1. **SSH into VPS and clone repo:**
   ```bash
   ssh user@your-vps-ip
   cd /var/www  # or your preferred directory
   git clone https://github.com/yourusername/fitscore.git
   cd fitscore
   ```

2. **Install system dependencies:**
   ```bash
   sudo apt update && sudo apt install -y python3.11 python3.11-venv git curl
   ```

3. **Run VPS setup:**
   ```bash
   make setup-vps
   ```

4. **Create `.env` file with production config:**
   ```bash
   cat > .env << 'EOF'
   SECRET_KEY=your-very-secure-random-key-here
   DEBUG=False
   DATABASE_URL=sqlite+aiosqlite:///./fitscore.db
   DATABASE_URL_SYNC=sqlite:///./fitscore.db
   EOF
   chmod 600 .env
   ```

5. **Create systemd service** (`/etc/systemd/system/fitscore.service`):
   ```ini
   [Unit]
   Description=FitScore FastAPI Application
   After=network.target

   [Service]
   Type=notify
   User=www-data
   WorkingDirectory=/var/www/fitscore
   Environment="PATH=/var/www/fitscore/venv/bin"
   EnvironmentFile=/var/www/fitscore/.env
   ExecStart=/var/www/fitscore/venv/bin/gunicorn main:app \
       -w 4 \
       -k uvicorn.workers.UvicornWorker \
       -b 127.0.0.1:8000
   Restart=always
   RestartSec=10
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=multi-user.target
   ```

6. **Enable and start service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start fitscore
   sudo systemctl enable fitscore
   ```

7. **Configure reverse proxy** (Nginx):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

### Ongoing Deployments

After each code change:
```bash
ssh user@your-vps-ip
cd /var/www/fitscore
make deploy  # Pulls latest code, installs deps, runs migrations, restarts
```

Or manually:
```bash
git pull origin main
venv/bin/pip install -r requirements.txt
venv/bin/alembic upgrade head
sudo systemctl restart fitscore
```

### Monitoring

Check service status:
```bash
sudo systemctl status fitscore
sudo journalctl -u fitscore -f  # Live logs
```
