import pytest


def test_register_success(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "new@test.com",
        "username": "newuser",
        "password": "Password1",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "new@test.com"
    assert data["role"] == "user"
    assert "hashed_password" not in data


def test_register_duplicate_email(client):
    payload = {"email": "dup@test.com", "username": "user1", "password": "Password1"}
    client.post("/api/v1/auth/register", json=payload)
    res = client.post("/api/v1/auth/register", json={**payload, "username": "user2"})
    assert res.status_code == 409


def test_register_weak_password(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "x@test.com", "username": "xuser", "password": "weakpw",
    })
    assert res.status_code == 422


def test_login_success(client):
    client.post("/api/v1/auth/register", json={
        "email": "login@test.com", "username": "loginuser", "password": "Password1",
    })
    res = client.post("/api/v1/auth/login", json={
        "email": "login@test.com", "password": "Password1",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()
    assert "refresh_token" in res.json()


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json={
        "email": "wp@test.com", "username": "wpuser", "password": "Password1",
    })
    res = client.post("/api/v1/auth/login", json={
        "email": "wp@test.com", "password": "WrongPass1",
    })
    assert res.status_code == 401


def test_me_requires_auth(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 403


def test_me_success(client, auth_headers):
    res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "user@test.com"


def test_refresh_token(client):
    client.post("/api/v1/auth/register", json={
        "email": "ref@test.com", "username": "refuser", "password": "Password1",
    })
    login = client.post("/api/v1/auth/login", json={
        "email": "ref@test.com", "password": "Password1",
    }).json()
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert res.status_code == 200
    assert "access_token" in res.json()
