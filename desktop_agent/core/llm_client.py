# desktop_agent/core/llm_client.py
import json
from typing import List, Dict
from desktop_agent.core.observer import Observation
from desktop_agent.core.provider import PROVIDER_REGISTRY, BaseProvider

# ========= 允许的动作 及参数约束 =========
ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "move", "click", "click_img",
                "type", "hotkey",
                "focus_window",
                "sleep", "finish"
            ]
        },
        "args": {
            "type": "object",
            "properties": {
                # 基础参数 —— 所有动作共用
                "x": {"type": "integer"},          # move / click
                "y": {"type": "integer"},
                "img": {"type": "string"},         # click_img
                "text": {"type": "string"},        # type
                "keys": {                          # hotkey
                    "type": "array",
                    "items": {"type": "string"},
                    "enum": [["ctrl", "s"], ["ctrl", "o"], ["alt", "f4"]]
                },
                "title": {"type": "string"},       # ← focus_window 只允许 title
                "duration": {"type": "number"},    # sleep
                "path": {"type": "string"}         # 自定义扩展，可忽略
            }
        }
    },
    "required": ["action"]
}

# ---------- L L M   C l i e n t ----------
class LLMClient:
    def __init__(self,
                 mode: str = "vision",
                 vendor: str = "openai",
                 model: str | None = None,
                 provider_kwargs: dict | None = None,
                 temperature: float = 0.2):
        self.mode = mode
        self.temperature = temperature
        provider_cls: type[BaseProvider] = PROVIDER_REGISTRY[vendor]
        self.provider = provider_cls(model=model, **(provider_kwargs or {}))

    # -------- 辅助：兼容对象 / dict ----------
    @staticmethod
    def _get_arguments(tool_call):
        return (
            tool_call.function.arguments
            if hasattr(tool_call, "function")
            else tool_call["function"]["arguments"]
        )

    # ---------------- 公开 API ----------------
    def get_plan(self, goal: str, obs: Observation) -> List[Dict]:
        msgs = self._build_messages(goal, obs, stage="plan")

        tools = [{
            "type": "function",
            "function": {
                "name": "return_plan",
                "description": "返回完成任务所需的原子动作序列",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "array",
                            "items": ACTION_SCHEMA
                        }
                    },
                    "required": ["plan"]
                }
            }
        }]

        res = self._chat(msgs, extra_tools=tools)

        if res["tool_calls"]:
            plan_obj = json.loads(
                self._get_arguments(res["tool_calls"][0])
            )
            return plan_obj["plan"]

        # fallback: 直接解析文本里的 [...]
        content = (res["content"] or "").strip()
        l, r = content.find("["), content.rfind("]")
        if l == -1 or r == -1:
            raise ValueError("LLM 未返回 JSON plan")
        return json.loads(content[l:r + 1])

    def next_action(self, goal: str, last_res: str,
                    obs: Observation, hist_tail: List[str]) -> Dict:

        msgs = self._build_messages(
            goal, obs, stage="step",
            last_result=last_res, history_tail=hist_tail
        )

        tools = [{
            "type": "function",
            "function": {
                "name": "action",
                "parameters": ACTION_SCHEMA
            }
        }]

        res = self._chat(msgs, extra_tools=tools)

        if res["tool_calls"]:
            args_json = self._get_arguments(res["tool_calls"][0])
            return json.loads(args_json)

        content = (res["content"] or "").strip()
        if not content or content[0] not in "{[":
            return {"action": "finish"}
        return json.loads(content)

    # ---------------- 内部 ----------------
    def _chat(self, messages, extra_tools=None):
        return self.provider.chat(
            messages=messages,
            temperature=self.temperature,
            tools=extra_tools
        )

    def _build_messages(self, goal, obs, stage,
                        last_result=None, history_tail=None):

        sys = (
            "你是 Windows 桌面自动化助手，只能输出结构化 JSON，"
            "且 action 必须在枚举列表中。"
            "focus_window 仅允许使用 title 字段，hotkey 仅限 [Ctrl+S] [Ctrl+O] [Alt+F4]。"
        )
        if self.mode == "text":
            sys += "你看不到截图，只能根据窗口标题和日志推断。"

        system = {"role": "system", "content": sys}

        if stage == "plan":
            return [
                system,
                {"role": "user",
                 "content": f"目标：{goal}\n"
                            "请直接调用函数 return_plan(plan=[...]) 返回动作序列。"},
                self._obs_msg(obs)
            ]

        tail = "\n".join(history_tail[-8:]) if history_tail else ""
        return [
            system,
            {"role": "assistant", "content": tail},
            {"role": "user",
             "content": f"目标：{goal}\n上一步结果：{last_result}\n"
                        "请调用函数 action(action={{...}}) 给出下一条动作。"},
            self._obs_msg(obs)
        ]

    def _obs_msg(self, obs: Observation):
        return (
            obs.as_vision_message("(当前截图)")
            if self.mode == "vision"
            else obs.as_text_message()
        )
