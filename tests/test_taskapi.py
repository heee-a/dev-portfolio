"""Task API 端到端测试（TestClient，内存级隔离：每个用例独立 db 文件）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "software" / "taskapi"))

import pytest
from fastapi.testclient import TestClient

import main as app_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TASK_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app_module.app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_get(client):
    r = client.post("/tasks", json={"title": "写周报", "priority": 1, "tags": ["工作"]})
    assert r.status_code == 201
    task = r.json()
    assert task["title"] == "写周报" and task["status"] == "todo" and task["priority"] == 1
    assert client.get(f"/tasks/{task['id']}").json()["title"] == "写周报"


def test_create_validation(client):
    assert client.post("/tasks", json={"title": ""}).status_code == 422
    assert client.post("/tasks", json={"title": "x", "priority": 9}).status_code == 422
    assert client.post("/tasks", json={}).status_code == 422


def test_update_lifecycle(client):
    tid = client.post("/tasks", json={"title": "A"}).json()["id"]
    r = client.patch(f"/tasks/{tid}", json={"status": "doing"})
    assert r.json()["status"] == "doing"
    r = client.patch(f"/tasks/{tid}", json={"status": "done", "priority": 3})
    assert r.json()["status"] == "done" and r.json()["priority"] == 3
    assert client.get("/tasks/stats").json()["done"] == 1


def test_update_404_and_delete(client):
    assert client.patch("/tasks/999", json={"status": "done"}).status_code == 404
    tid = client.post("/tasks", json={"title": "B"}).json()["id"]
    assert client.delete(f"/tasks/{tid}").status_code == 204
    assert client.get(f"/tasks/{tid}").status_code == 404
    assert client.delete(f"/tasks/{tid}").status_code == 404


def test_list_pagination_and_filter(client):
    for i in range(5):
        client.post("/tasks", json={"title": f"任务{i}", "priority": i % 3 + 1})
    client.patch("/tasks/1", json={"status": "done"})
    body = client.get("/tasks", params={"status": "todo"}).json()
    assert len(body) == 4 and all(t["status"] == "todo" for t in body)
    body = client.get("/tasks", params={"limit": 2, "offset": 2}).json()
    assert len(body) == 2
    body = client.get("/tasks", params={"q": "任务3"}).json()
    assert len(body) == 1 and body[0]["title"] == "任务3"
    stats = client.get("/tasks/stats").json()
    assert stats == {"total": 5, "todo": 4, "doing": 0, "done": 1,
                     "completion_rate": 20.0}
