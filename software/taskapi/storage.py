"""任务管理 API 的数据模型与存储层（SQLite，线程安全）。"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Task:
    id: int
    title: str
    status: str = "todo"          # todo / doing / done
    priority: int = 2              # 1 高 2 中 3 低
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class TaskStore:
    """SQLite 存储层。写操作串行化（锁），读并发安全。

    设计决策：
    - SQLite 单文件零运维，适合演示；换 PostgreSQL 只需改本层；
    - tags 以 JSON 文本存储，查询需求变复杂后应拆关联表；
    - 时间戳由存储层生成（UTC ISO8601），客户端不可伪造。
    """

    def __init__(self, db_path: str | Path = "tasks.db"):
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'todo'
                            CHECK (status IN ('todo', 'doing', 'done')),
                priority    INTEGER NOT NULL DEFAULT 2 CHECK (priority BETWEEN 1 AND 3),
                tags        TEXT NOT NULL DEFAULT '[]',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    @staticmethod
    def _now() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"], title=row["title"], status=row["status"],
            priority=row["priority"], tags=json.loads(row["tags"]),
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    def create(self, title: str, priority: int = 2, tags: list[str] | None = None) -> Task:
        now = self._now()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO tasks (title, priority, tags, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (title, priority, json.dumps(tags or [], ensure_ascii=False), now, now))
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
        return self._row_to_task(row)

    def get(self, task_id: int) -> Task | None:
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def list(self, status: str | None = None, q: str | None = None,
             limit: int = 20, offset: int = 0) -> tuple[list[Task], int]:
        """返回 (任务列表, 总数)；q 对 title 做子串搜索。"""
        where, args = [], []
        if status:
            where.append("status = ?")
            args.append(status)
        if q:
            where.append("title LIKE ?")
            args.append(f"%{q}%")
        cond = f"WHERE {' AND '.join(where)}" if where else ""
        total = self._conn.execute(
            f"SELECT COUNT(*) FROM tasks {cond}", args).fetchone()[0]
        rows = self._conn.execute(
            f"SELECT * FROM tasks {cond} "
            "ORDER BY priority ASC, updated_at DESC LIMIT ? OFFSET ?",
            args + [limit, offset]).fetchall()
        return [self._row_to_task(r) for r in rows], total

    def update(self, task_id: int, **fields) -> Task | None:
        if self.get(task_id) is None:
            return None
        sets, args = [], []
        for key in ("title", "status", "priority"):
            if key in fields and fields[key] is not None:
                sets.append(f"{key} = ?")
                args.append(fields[key])
        if "tags" in fields and fields["tags"] is not None:
            sets.append("tags = ?")
            args.append(json.dumps(fields["tags"], ensure_ascii=False))
        if not sets:
            return self.get(task_id)
        sets.append("updated_at = ?")
        args.append(self._now())
        args.append(task_id)
        with self._lock:
            self._conn.execute(
                f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", args)
            self._conn.commit()
        return self.get(task_id)

    def delete(self, task_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            self._conn.commit()
        return cur.rowcount > 0

    def stats(self) -> dict:
        rows = self._conn.execute(
            "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status").fetchall()
        by_status = {r["status"]: r["n"] for r in rows}
        return {
            "total": sum(by_status.values()),
            "todo": by_status.get("todo", 0),
            "doing": by_status.get("doing", 0),
            "done": by_status.get("done", 0),
            "completion_rate": round(by_status.get("done", 0)
                                     / max(1, sum(by_status.values())) * 100, 1),
        }
