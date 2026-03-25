# Podium - Sistema de Gestion de Competencias CrossFit

Sistema completo para gestionar competencias de CrossFit con sistema de puntuacion Podium, incluyendo panel de administracion, vista de jueces, leaderboard publico y sistema de auditoria.

## Caracteristicas

- **Panel de Administracion**: CRUD completo para competencias, atletas y WODs
- **Vista de Jueces**: Ingreso rapido de scores con busqueda de atletas
- **Leaderboard Publico**: Actualizacion automatica con tabs por division
- **Sistema de Puntuacion Podium**: Calculo automatico de rankings y puntos
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
- `POST /api/admin/competitions/{id}/teams` - Agregar equipo (modo equipos)
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

## Sistema de Puntuacion Podium

### Logica de Ranking por WOD

Los atletas se ranquean **dentro de su propia division** (no contra el campo completo).

Direccion segun tipo de WOD:
- **time**: menor tiempo = mejor posicion
- **amrap / reps / calories / load / distance**: mayor valor = mejor posicion

### Puntos por WOD

```
puntos = total_atletas_en_division - rank + 1
```

Ejemplo con 5 atletas en la division:

| Posicion | Puntos |
|----------|--------|
| 1º | 5 |
| 2º | 4 |
| 3º | 3 |
| 4º | 2 |
| 5º | 1 |
| DNF/DNS (sin resultado) | 0 |

### Empates dentro de un WOD

Dos atletas empatan si tienen **exactamente el mismo resultado Y el mismo tiebreak**.
- Ambos reciben el mismo rank y los mismos puntos.
- El siguiente rank se salta (ej: dos atletas empatan en 1º → el siguiente es 3º).

### Puntuacion Final

Suma de puntos obtenidos en todos los WODs de la competencia.

### Criterio de desempate en el leaderboard (countback)

Cuando dos atletas tienen el mismo total de puntos se aplica el metodo **countback** (estandar CrossFit):

1. Mayor cantidad de **1eros puestos** en WODs individuales.
2. Si siguen iguales → mayor cantidad de **2dos puestos**.
3. Luego 3eros, 4tos, etc.
4. Si todo lo anterior es identico → **menor numero de dorsal** (bib_number).

El countback garantiza que siempre haya un ganador claro en el leaderboard final.

## Divisiones Soportadas

- Libre Masculino / Femenino
- Scaled Masculino / Femenino
- Master +40 Masculino / Femenino
- Novato Masculino / Femenino
- Equipos (competencias en modo equipo)

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
DATABASE_URL=sqlite+aiosqlite:///./data/podium.db
```

### Con Gunicorn

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## Licencia

MIT License
