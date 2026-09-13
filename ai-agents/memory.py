"""对话记忆：滑动窗口，防止长对话超出上下文。"""

from __future__ import annotations

from dataclasses import dataclass, field

from llm import Message


@dataclass
class ConversationMemory:
    """保留 system 提示 + 最近 max_turns 轮（一轮 = user + assistant）。"""

    max_turns: int = 8
    history: list[Message] = field(default_factory=list)

    def add(self, message: Message) -> None:
        self.history.append(message)

    def window(self, system: str) -> list[Message]:
        trimmed = self.history[-(self.max_turns * 2):]
        return [Message("system", system)] + trimmed

    def clear(self) -> None:
        self.history.clear()
