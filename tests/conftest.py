"""
Shared test fixtures for Podium test suite.
"""

from datetime import date

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from auth import create_access_token, get_password_hash
from config import Roles
from database import Base, get_db
from main import app
from models import WOD, Athlete, Competition, User

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    SessionLocal = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(
        username="testadmin",
        password_hash=get_password_hash("adminpass"),
        role=Roles.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def judge_user(db_session):
    user = User(
        username="testjudge",
        password_hash=get_password_hash("judgepass"),
        role=Roles.JUDGE,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
def admin_token(admin_user):
    return create_access_token(
        data={
            "sub": str(admin_user.id),
            "username": admin_user.username,
            "role": admin_user.role,
        }
    )


@pytest_asyncio.fixture
def judge_token(judge_user):
    return create_access_token(
        data={
            "sub": str(judge_user.id),
            "username": judge_user.username,
            "role": judge_user.role,
        }
    )


@pytest_asyncio.fixture
async def competition(db_session, admin_user):
    comp = Competition(
        name="Test Competition",
        date=date(2026, 4, 7),
        is_active=True,
        created_by=admin_user.id,
    )
    db_session.add(comp)
    await db_session.flush()
    await db_session.refresh(comp)
    return comp


@pytest_asyncio.fixture
async def athlete(db_session, competition):
    a = Athlete(
        name="Alice Test",
        gender="Femenino",
        division="Libre Femenino",
        bib_number="001",
        competition_id=competition.id,
    )
    db_session.add(a)
    await db_session.flush()
    await db_session.refresh(a)
    return a


@pytest_asyncio.fixture
async def wod(db_session, competition):
    w = WOD(
        name="WOD 1",
        wod_type="time",
        order_in_competition=1,
        competition_id=competition.id,
    )
    db_session.add(w)
    await db_session.flush()
    await db_session.refresh(w)
    return w
