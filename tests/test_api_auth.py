"""
Integration tests for authentication API endpoints.
"""

import pytest


@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    resp = await client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "adminpass"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    resp = await client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "wrongpass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post(
        "/api/auth/login",
        data={"username": "nobody", "password": "pass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_json_success(client, admin_user):
    resp = await client.post(
        "/api/auth/login/json",
        json={"username": "testadmin", "password": "adminpass"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_get_me_authenticated(client, admin_user, admin_token):
    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testadmin"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_users_admin_only(client, admin_user, admin_token, judge_user):
    resp = await client.get(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "testadmin" in usernames
    assert "testjudge" in usernames


@pytest.mark.asyncio
async def test_list_users_forbidden_for_judge(client, judge_user, judge_token):
    resp = await client.get(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {judge_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_user(client, admin_user, admin_token):
    resp = await client.post(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "newjudge",
            "password": "pass1234",
            "role": "judge",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "newjudge"
    assert resp.json()["role"] == "judge"


@pytest.mark.asyncio
async def test_logout(client):
    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 200
