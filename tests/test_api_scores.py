"""
Integration tests for scores API endpoints.
Covers score submission, retrieval, update, verification, deletion,
and ranking recalculation.
"""

import pytest

from models import WOD, Athlete


@pytest.mark.asyncio
async def test_create_score(client, admin_token, athlete, wod):
    resp = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": athlete.id, "wod_id": wod.id, "raw_result": 300.0},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["athlete_id"] == athlete.id
    assert data["wod_id"] == wod.id
    assert data["raw_result"] == 300.0
    assert data["status"] == "pending"
    assert data["rank"] == 1
    assert data["points"] == 1


@pytest.mark.asyncio
async def test_create_score_duplicate(client, admin_token, athlete, wod):
    payload = {"athlete_id": athlete.id, "wod_id": wod.id, "raw_result": 300.0}
    await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    resp = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_score_unknown_athlete(client, admin_token, wod):
    resp = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": 9999, "wod_id": wod.id, "raw_result": 300.0},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_score_requires_auth(client, athlete, wod):
    resp = await client.post(
        "/api/scores",
        json={"athlete_id": athlete.id, "wod_id": wod.id, "raw_result": 300.0},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_score(client, admin_token, athlete, wod):
    create_resp = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": athlete.id, "wod_id": wod.id, "raw_result": 250.0},
    )
    score_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/scores/{score_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == score_id


@pytest.mark.asyncio
async def test_get_score_not_found(client, admin_token):
    resp = await client.get(
        "/api/scores/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_scores(client, admin_token, athlete, wod):
    await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": athlete.id, "wod_id": wod.id, "raw_result": 300.0},
    )
    resp = await client.get(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_update_score(client, admin_token, athlete, wod):
    create_resp = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": athlete.id, "wod_id": wod.id, "raw_result": 300.0},
    )
    score_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/scores/{score_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"raw_result": 280.0, "notes": "corrected"},
    )
    assert resp.status_code == 200
    assert resp.json()["raw_result"] == 280.0
    assert resp.json()["notes"] == "corrected"


@pytest.mark.asyncio
async def test_verify_score(client, admin_token, athlete, wod):
    create_resp = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": athlete.id, "wod_id": wod.id, "raw_result": 300.0},
    )
    score_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/scores/{score_id}/verify",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"
    assert resp.json()["verified_at"] is not None


@pytest.mark.asyncio
async def test_delete_score(client, admin_token, athlete, wod):
    create_resp = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": athlete.id, "wod_id": wod.id, "raw_result": 300.0},
    )
    score_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/scores/{score_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    get_resp = await client.get(
        f"/api/scores/{score_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_ranking_recalculation_time_wod(
    client, admin_token, db_session, competition
):
    """
    Two athletes in same division on a time WOD.
    Lower time should rank 1st and earn more points.
    """
    a1 = Athlete(
        name="Fast Alice",
        gender="Femenino",
        division="Libre Femenino",
        bib_number="010",
        competition_id=competition.id,
    )
    a2 = Athlete(
        name="Slow Bob",
        gender="Femenino",
        division="Libre Femenino",
        bib_number="011",
        competition_id=competition.id,
    )
    db_session.add_all([a1, a2])
    await db_session.flush()
    await db_session.refresh(a1)
    await db_session.refresh(a2)

    w = WOD(
        name="WOD Time",
        wod_type="time",
        order_in_competition=1,
        competition_id=competition.id,
    )
    db_session.add(w)
    await db_session.flush()
    await db_session.refresh(w)

    # a1 = 200s (faster), a2 = 300s (slower)
    r1 = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": a1.id, "wod_id": w.id, "raw_result": 200.0},
    )
    r2 = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": a2.id, "wod_id": w.id, "raw_result": 300.0},
    )
    score1_id = r1.json()["id"]

    # r2's response reflects the post-recalculation state
    assert r2.json()["rank"] == 2
    assert r2.json()["points"] == 1

    # Fetch score 1 again — recalculation after r2 updated its rank/points
    fetched = await client.get(
        f"/api/scores/{score1_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert fetched.json()["rank"] == 1
    assert fetched.json()["points"] == 2


@pytest.mark.asyncio
async def test_ranking_recalculation_amrap_wod(
    client, admin_token, db_session, competition
):
    """
    Two athletes on an AMRAP WOD. Higher reps = 1st.
    """
    a1 = Athlete(
        name="High Reps",
        gender="Masculino",
        division="Libre Masculino",
        bib_number="020",
        competition_id=competition.id,
    )
    a2 = Athlete(
        name="Low Reps",
        gender="Masculino",
        division="Libre Masculino",
        bib_number="021",
        competition_id=competition.id,
    )
    db_session.add_all([a1, a2])
    await db_session.flush()
    await db_session.refresh(a1)
    await db_session.refresh(a2)

    w = WOD(
        name="AMRAP 20",
        wod_type="amrap",
        order_in_competition=2,
        competition_id=competition.id,
    )
    db_session.add(w)
    await db_session.flush()
    await db_session.refresh(w)

    r1 = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": a1.id, "wod_id": w.id, "raw_result": 80.0},
    )
    r2 = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": a2.id, "wod_id": w.id, "raw_result": 60.0},
    )

    assert r1.json()["rank"] == 1
    assert r2.json()["rank"] == 2


@pytest.mark.asyncio
async def test_judge_can_submit_score(client, judge_token, athlete, wod):
    resp = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {judge_token}"},
        json={"athlete_id": athlete.id, "wod_id": wod.id, "raw_result": 400.0},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_judge_cannot_delete_score(
    client, admin_token, judge_token, athlete, wod
):
    create_resp = await client.post(
        "/api/scores",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"athlete_id": athlete.id, "wod_id": wod.id, "raw_result": 300.0},
    )
    score_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/scores/{score_id}",
        headers={"Authorization": f"Bearer {judge_token}"},
    )
    assert resp.status_code == 403
