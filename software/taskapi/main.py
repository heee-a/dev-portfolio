"""FastAPI 应用：路由层只做参数绑定与状态码，校验在 schemas、业务在 storage。

启动: uvicorn main:app --reload   或   python run.py
文档: http://127.0.0.1:8000/docs  (Swagger 自动生成)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query

from schemas import TaskCreate, TaskUpdate
from storage import Task, TaskStore

_store: TaskStore | None = None


def get_store() -> TaskStore:
    assert _store is not None
    return _store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """数据库路径可由环境变量 TASK_DB_PATH 覆盖（12-factor 配置外置）。"""
    global _store
    db = Path(os.environ.get("TASK_DB_PATH", Path(__file__).parent / "tasks.db"))
    _store = TaskStore(db)
    yield
    _store = None


app = FastAPI(
    title="Task API",
    description="任务管理 REST API：CRUD / 分页搜索 / 统计。教学用完整后端示例。",
    version="1.0.0",
    lifespan=lifespan,
)


def _dump(task: Task) -> dict:
    return task.__dict__


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/tasks", response_model=list[Task], tags=["tasks"])
def list_tasks(
    status: str | None = Query(None, pattern="^(todo|doing|done)$"),
    q: str | None = Query(None, max_length=50, description="标题子串搜索"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    store: TaskStore = Depends(get_store),
) -> list[Task]:
    tasks, _total = store.list(status=status, q=q, limit=limit, offset=offset)
    return tasks


@app.get("/tasks/stats", tags=["tasks"])
def task_stats(store: TaskStore = Depends(get_store)) -> dict:
    return store.stats()


@app.get("/tasks/{task_id}", response_model=Task, tags=["tasks"])
def get_task(task_id: int, store: TaskStore = Depends(get_store)) -> Task:
    task = store.get(task_id)
    if task is None:
        raise HTTPException(404, detail=f"task {task_id} not found")
    return task


@app.post("/tasks", response_model=Task, status_code=201, tags=["tasks"])
def create_task(body: TaskCreate, store: TaskStore = Depends(get_store)) -> Task:
    return store.create(body.title, body.priority, body.tags)


@app.patch("/tasks/{task_id}", response_model=Task, tags=["tasks"])
def update_task(task_id: int, body: TaskUpdate,
                store: TaskStore = Depends(get_store)) -> Task:
    task = store.update(task_id, **body.model_dump(exclude_none=True))
    if task is None:
        raise HTTPException(404, detail=f"task {task_id} not found")
    return task


@app.delete("/tasks/{task_id}", status_code=204, tags=["tasks"])
def delete_task(task_id: int, store: TaskStore = Depends(get_store)) -> None:
    if not store.delete(task_id):
        raise HTTPException(404, detail=f"task {task_id} not found")
