# FitScore - Sistema de Gestion de Competencias CrossFit

Sistema completo para gestionar competencias de CrossFit con sistema de puntuacion FitScore, incluyendo panel de administracion, vista de jueces, leaderboard publico y sistema de auditoria.

## Caracteristicas

- **Panel de Administracion**: CRUD completo para competencias, atletas y WODs
- **Vista de Jueces**: Ingreso rapido de scores con busqueda de atletas
- **Leaderboard Publico**: Actualizacion automatica con tabs por division
- **Sistema de Puntuacion FitScore**: Calculo automatico de rankings y puntos
- **Auditoria**: Log completo de cambios en scores
- **Exportacion**: PDF, Excel y CSV de resultados
- **Importacion**: Carga masiva de atletas via CSV

## Stack Tecnologico

- **Backend**: FastAPI + SQLAlchemy (async) + SQLite
- **Frontend**: Jinja2 + TailwindCSS (CDN) + Alpine.js
- **Auth**: JWT con roles (admin, judge, viewer)
- **Exportacion**: openpyxl (Excel), reportlab (PDF)
- **Migraciones**: Alembic

## Instalacion

### Requisitos Previos

- Python 3.11+
- pip

### Instalacion Local

```bash
# Clonar repositorio
cd fitscore

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Crear datos de prueba
python seed.py

# Ejecutar aplicacion
uvicorn main:app --reload
```

### Con Docker

```bash
# Desarrollo
docker-compose --profile dev up

# Produccion
docker-compose up -d
```

Acceder a: http://localhost:8000

## Credenciales de Prueba

| Usuario | Contrasena | Rol |
|---------|------------|-----|
| admin | admin123 | Administrador |
| judge1 | judge123 | Juez |
| judge2 | judge123 | Juez |
| viewer | viewer123 | Espectador |

## Estructura del Proyecto

```
fitscore/
├── main.py                 # Entry point FastAPI
├── config.py               # Configuracion y constantes
├── database.py             # SQLAlchemy setup
├── models.py               # Modelos ORM
├── schemas.py              # Pydantic schemas
├── auth.py                 # JWT y autenticacion
├── routers/
│   ├── admin.py            # CRUD competencias, atletas, WODs
│   ├── auth.py             # Login/logout
│   ├── scores.py           # Ingreso de scores
│   ├── leaderboard.py      # Leaderboard publico
│   ├── audit.py            # Log de auditoria
│   └── export.py           # Exportacion PDF/Excel/CSV
├── scoring/
│   └── fitscore.py         # Algoritmo de puntuacion
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── admin/              # Vistas admin
│   ├── judge/              # Vistas juez
│   └── public/             # Leaderboard publico
├── static/css/
├── alembic/                # Migraciones
├── seed.py                 # Datos de prueba
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## API Endpoints

### Autenticacion
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Usuario actual
- `GET /api/auth/users` - Listar usuarios (admin)

### Admin
- `GET/POST /api/admin/competitions` - CRUD competencias
- `GET/POST /api/admin/athletes` - CRUD atletas
- `POST /api/admin/competitions/{id}/athletes/import` - Importar CSV
- `GET/POST /api/admin/wods` - CRUD WODs

### Scores
- `GET/POST /api/scores` - CRUD scores
- `POST /api/scores/{id}/verify` - Verificar score
- `GET /api/scores/search/athlete` - Buscar atleta

### Leaderboard
- `GET /api/leaderboard/{competition_id}` - Leaderboard completo
- `GET /api/leaderboard/{competition_id}/division/{division}` - Por division
- `GET /api/leaderboard/{competition_id}/wods` - Lista de WODs

### Exportacion
- `GET /api/export/{competition_id}/excel` - Exportar Excel
- `GET /api/export/{competition_id}/pdf` - Exportar PDF
- `GET /api/export/{competition_id}/csv` - Exportar CSV

### Auditoria
- `GET /api/audit` - Log de auditoria
- `GET /api/audit/score/{id}` - Historial de un score

## Sistema de Puntuacion FitScore

### Logica de Ranking
- **For Time**: Menor tiempo = mejor posicion
- **AMRAP/Reps/Calories/Load**: Mayor valor = mejor posicion
- Empates: Mismo puesto, mismo puntaje, siguiente posicion se salta

### Puntos
- 1er lugar = N puntos (N = total de atletas en division)
- 2do lugar = N-1 puntos
- ...
- Ultimo lugar = 1 punto
- DNF/DNS = 0 puntos

### FitScore Final
Suma de puntos obtenidos en todos los WODs.

## Divisiones Soportadas

- RX Masculino / Femenino
- Scaled Masculino / Femenino
- Master +40 Masculino / Femenino
- Master +50 Masculino / Femenino
- Teen Masculino / Femenino

## Tipos de WOD

- **time**: For Time (menor es mejor)
- **amrap**: AMRAP - repeticiones (mayor es mejor)
- **load**: Max Load en kg (mayor es mejor)
- **reps**: Max Reps (mayor es mejor)
- **calories**: Calorias (mayor es mejor)
- **distance**: Distancia en metros (mayor es mejor)

## Importacion de Atletas (CSV)

Formato esperado:
```csv
name,gender,birth_date,division,box,bib_number
Juan Perez,Masculino,1990-05-15,RX Masculino,CrossFit Central,001
Maria Garcia,Femenino,1992-08-20,RX Femenino,CrossFit Norte,002
```

Descargar plantilla en: `/api/export/{competition_id}/athletes/template`

## Migraciones

```bash
# Crear nueva migracion
alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
alembic upgrade head

# Revertir
alembic downgrade -1
```

## Desarrollo

### Ejecutar Tests
```bash
pytest
```

### Documentacion API
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Produccion

### Variables de Entorno

```bash
SECRET_KEY=tu-clave-secreta-segura
DEBUG=False
DATABASE_URL=sqlite+aiosqlite:///./data/fitscore.db
```

### Con Gunicorn

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## Licencia

MIT License
