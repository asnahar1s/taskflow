def test_create_task(client, auth_headers):
    res = client.post("/api/v1/tasks/", json={
        "title": "My Task", "description": "Do something", "priority": "high",
    }, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "My Task"
    assert data["status"] == "todo"


def test_create_task_unauthenticated(client):
    res = client.post("/api/v1/tasks/", json={"title": "Task"})
    assert res.status_code == 403


def test_list_tasks(client, auth_headers):
    client.post("/api/v1/tasks/", json={"title": "T1"}, headers=auth_headers)
    client.post("/api/v1/tasks/", json={"title": "T2"}, headers=auth_headers)
    res = client.get("/api/v1/tasks/", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2


def test_get_task(client, auth_headers):
    task = client.post("/api/v1/tasks/", json={"title": "GetMe"}, headers=auth_headers).json()
    res = client.get(f"/api/v1/tasks/{task['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["title"] == "GetMe"


def test_update_task(client, auth_headers):
    task = client.post("/api/v1/tasks/", json={"title": "Old"}, headers=auth_headers).json()
    res = client.patch(f"/api/v1/tasks/{task['id']}", json={
        "title": "New", "status": "in_progress",
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["title"] == "New"
    assert res.json()["status"] == "in_progress"


def test_delete_task(client, auth_headers):
    task = client.post("/api/v1/tasks/", json={"title": "Delete me"}, headers=auth_headers).json()
    res = client.delete(f"/api/v1/tasks/{task['id']}", headers=auth_headers)
    assert res.status_code == 200
    # Task should no longer be accessible
    get_res = client.get(f"/api/v1/tasks/{task['id']}", headers=auth_headers)
    assert get_res.status_code == 404


def test_cannot_access_other_users_task(client, auth_headers, admin_headers):
    # Admin creates a task
    task = client.post("/api/v1/tasks/", json={"title": "Admin task"}, headers=admin_headers).json()
    # Regular user should be forbidden
    res = client.get(f"/api/v1/tasks/{task['id']}", headers=auth_headers)
    assert res.status_code == 403


def test_admin_sees_all_tasks(client, auth_headers, admin_headers):
    client.post("/api/v1/tasks/", json={"title": "User task"}, headers=auth_headers)
    client.post("/api/v1/tasks/", json={"title": "Admin task"}, headers=admin_headers)
    res = client.get("/api/v1/tasks/", headers=admin_headers)
    assert res.json()["total"] == 2


def test_filter_tasks_by_status(client, auth_headers):
    client.post("/api/v1/tasks/", json={"title": "T1", "status": "todo"}, headers=auth_headers)
    t2 = client.post("/api/v1/tasks/", json={"title": "T2"}, headers=auth_headers).json()
    client.patch(f"/api/v1/tasks/{t2['id']}", json={"status": "done"}, headers=auth_headers)
    res = client.get("/api/v1/tasks/?status=done", headers=auth_headers)
    assert res.json()["total"] == 1


def test_pagination(client, auth_headers):
    for i in range(5):
        client.post("/api/v1/tasks/", json={"title": f"Task {i}"}, headers=auth_headers)
    res = client.get("/api/v1/tasks/?page=1&page_size=3", headers=auth_headers)
    assert len(res.json()["tasks"]) == 3
    assert res.json()["total"] == 5
