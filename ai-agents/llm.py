"""LLM 抽象层：OpenAI 兼容接口 + 可脚本化的 FakeLLM（离线测试/教学演示）。

DeepSeek / Kimi / 智谱 GLU / 通义 等主流服务都提供 OpenAI 兼容端点，
换模型只需换 base_url / api_key / model 三个环境变量。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str                     # system / user / assistant
    content: str


class BaseLLM:
    def chat(self, messages: list[Message]) -> str:
        raise NotImplementedError


class OpenAICompatLLM(BaseLLM):
    """调用任意 OpenAI 兼容 /chat/completions 端点。"""

    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 model: str | None = None, temperature: float = 0.2):
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "")
                         ).rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or os.environ.get("OPENAI_MODEL", "")
        self.temperature = temperature
        if not (self.base_url and self.api_key and self.model):
            raise RuntimeError(
                "需要环境变量 OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL"
                "（DeepSeek/Kimi/智谱 等 OpenAI 兼容服务均可）")

    def chat(self, messages: list[Message]) -> str:
        import requests

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "temperature": self.temperature,
                  "messages": [{"role": m.role, "content": m.content}
                               for m in messages]},
            timeout=120)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


@dataclass
class FakeLLM(BaseLLM):
    """按脚本顺序回放回复——离线测试与教学演示用，明确标注非真实模型。"""

    script: list[str] = field(default_factory=list)
    calls: list[list[Message]] = field(default_factory=list)

    def chat(self, messages: list[Message]) -> str:
        self.calls.append(messages)
        if not self.script:
            raise RuntimeError("FakeLLM 脚本已耗尽")
        return self.script.pop(0)
