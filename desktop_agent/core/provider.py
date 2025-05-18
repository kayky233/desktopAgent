# provider.py
from __future__ import annotations
import os, requests, openai
from abc import ABC, abstractmethod
from typing import List, Dict

# ---------- 判断 SDK 版本 ----------
def _is_v1() -> bool:
    """openai-python ≥1.0.x 才有 openai.resources 或 openai.chat"""
    return hasattr(openai, "chat")

# ---------- 抽象基类 ----------
class BaseProvider(ABC):
    def __init__(self, model: str, **kw):
        self.model = model
        self.kw = kw

    @abstractmethod
    def chat(
        self,
        messages: List[Dict],
        temperature: float,
        tools: List[Dict] | None = None
    ) -> Dict: ...

# ---------- OpenAI ----------
class OpenAIProvider(BaseProvider):
    def __init__(self, model: str, api_key: str | None = None, **kw):
        super().__init__(model, **kw)
        openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
        print("[DEBUG] OpenAIProvider init, model =", model)

    def chat(self, messages, temperature, tools=None):
        call_args = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            tools=tools or []
        )

        if _is_v1():  # ≥1.0.x
            rsp = openai.chat.completions.create(**call_args).choices[0].message
        else:         # 0.28.x
            rsp = openai.ChatCompletion.create(**call_args).choices[0].message

        return {
            "content": rsp.content or "",
            "tool_calls": getattr(rsp, "tool_calls", []) or []
        }

# ---------- Azure OpenAI ----------
class AzureProvider(BaseProvider):
    """
    AzureProvider(
        deployment="gpt4o",
        api_key   ="<key>",
        endpoint  ="https://xxx.openai.azure.com",
        api_version="2024-02-15-preview"
    )
    """
    def __init__(
        self,
        deployment: str,
        api_key: str,
        endpoint: str,
        api_version: str = "2024-02-15-preview",
        **kw
    ):
        super().__init__(model=deployment)
        self.deployment = deployment
        self.api_version = api_version

        endpoint = endpoint.rstrip("/")

        if _is_v1():  # 新 SDK：实例化客户端
            from openai import AzureOpenAI
            self.client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_version
            )
        else:         # 旧 SDK：全局配置
            openai.api_type = "azure"
            openai.api_key = api_key
            openai.api_base = endpoint
            openai.api_version = api_version
            self.client = openai

    def chat(self, messages, temperature, tools=None):
        call_args = dict(
            messages=messages,
            temperature=temperature,
            tools=tools or []
        )

        if _is_v1():
            # v1.x 用 model 字段
            rsp = self.client.chat.completions.create(
                model=self.deployment, **call_args
            ).choices[0].message
        else:
            # v0.28 用 engine 字段
            rsp = self.client.ChatCompletion.create(
                engine=self.deployment, **call_args
            ).choices[0].message

        return {
            "content": rsp.content or "",
            "tool_calls": getattr(rsp, "tool_calls", []) or []
        }

# ---------- DeepSeek (OpenAI compatible) ----------
class DeepSeekProvider(BaseProvider):
    """
    DeepSeekProvider(
        model="deepseek-chat",
        api_key="sk-...",
        base_url="https://api.deepseek.com/v1"   # 或 endpoint
    )
    """
    def __init__(self,
                 model: str,
                 api_key: str,
                 base_url: str | None = None,
                 endpoint: str | None = None,
                 **kw):
        super().__init__(model)
        self.base_url = (base_url or endpoint or
                         "https://api.deepseek.com/v1").rstrip("/")
        self.api_key  = api_key

        # -------- 区分 SDK 版本 --------
        if _is_v1():                                  # openai-python ≥1.0
            from openai import OpenAI                 # 实例化客户端
            self.client = OpenAI(
                api_key  = api_key,
                base_url = self.base_url
            )
        else:                                         # openai-python <1.0
            openai.api_key  = api_key
            openai.api_base = self.base_url
            self.client = openai

        print("[DEBUG] DeepSeek client ready:", self.base_url)

    def chat(self,
             messages: List[Dict],
             temperature: float,
             tools: List[Dict] | None = None) -> Dict:

        call_args = dict(
            model=self.model,
            messages=messages,
            temperature=temperature
        )
        if tools:  # ← 关键改动
            call_args["tools"] = tools

        if _is_v1():
            rsp = self.client.chat.completions.create(
                timeout=60, **call_args
            ).choices[0].message
        else:
            rsp = self.client.ChatCompletion.create(
                timeout=60, **call_args
            ).choices[0].message

        return {
            "content": rsp.content or "",
            "tool_calls": getattr(rsp, "tool_calls", []) or []
        }


# ---------- 本地 HuggingFace TGI ----------
class HFLocalProvider(BaseProvider):
    def __init__(self, model: str, endpoint: str):
        super().__init__(model)
        self.endpoint = endpoint.rstrip("/")

    def chat(self, messages, temperature, tools=None):
        prompt = "\n".join(
            m["content"] for m in messages if m["role"] != "system"
        )
        data = {
            "inputs": prompt,
            "parameters": {"temperature": temperature, "max_new_tokens": 512}
        }
        rsp = requests.post(
            f"{self.endpoint}/generate", json=data, timeout=60
        ).json()
        return {"content": rsp["generated_text"], "tool_calls": []}

# ---------- Provider Registry ----------
PROVIDER_REGISTRY = {
    "openai":   OpenAIProvider,
    "azure":    AzureProvider,
    "deepseek": DeepSeekProvider,
    "hf_local": HFLocalProvider,
}
