"""Pydantic 请求模型：入参校验集中在这一层，路由保持轻薄。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    priority: Literal[1, 2, 3] = 2          # 1 高 2 中 3 低
    tags: list[str] = Field(default_factory=list, max_length=5)


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=100)
    status: Literal["todo", "doing", "done"] | None = None
    priority: Literal[1, 2, 3] | None = None
    tags: list[str] | None = Field(None, max_length=5)
