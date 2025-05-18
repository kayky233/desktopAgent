# llm_client.py  ―― 完整替换版
import json
from typing import List, Dict
from observer import Observation
from provider import PROVIDER_REGISTRY, BaseProvider

# ---------------- 动作 JSON 模式 ----------------
ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string"},
        "args":   {"type": "object"}
    },
    "required": ["action"]
}

# ---------- LLMClient ----------
class LLMClient:
    def __init__(self,
                 mode: str = "vision",          # vision | text
                 vendor: str = "openai",        # openai | azure | deepseek | hf_local
                 model: str | None = None,
                 provider_kwargs: dict | None = None,
                 temperature: float = 0.2):
        self.mode = mode
        self.temperature = temperature
        provider_cls: type[BaseProvider] = PROVIDER_REGISTRY[vendor]
        self.provider = provider_cls(model=model, **(provider_kwargs or {}))

    # ---------- 帮助函数：跨版本取 arguments ----------
    def _get_arguments(self,tool_call):
        """
        tool_call 可能是 ChatCompletionMessageToolCall(v1) 或 dict(v0.28)。
        返回 JSON 字符串 arguments。
        """
        if hasattr(tool_call, "function"):  # v1.x
            return tool_call.function.arguments
        else:  # v0.28
            return tool_call["function"]["arguments"]

    # ---------------- 公开 API ----------------
    def get_plan(self, goal: str, obs: Observation) -> List[Dict]:
        """
        让 LLM 一次性返回完整 plan。
        使用 function-calling：return_plan({ plan: [ ... ] })
        """
        msgs = self._build_messages(goal, obs, stage="plan")

        # --- function 定义：返回对象，内部字段 plan 是动作数组 ---
        tools = [{
            "type": "function",
            "function": {
                "name": "return_plan",
                "description": "返回完成任务的原子动作顺序数组",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "array",
                            "items": ACTION_SCHEMA,
                        }
                    },
                    "required": ["plan"]
                }
            }
        }]

        res = self._chat(msgs, extra_tools=tools)

        # 解析函数调用
        if res["tool_calls"]:
            args_json = self._get_arguments(res["tool_calls"][0])
            plan_obj = json.loads(args_json)  # {"plan":[ ... ]}
            return plan_obj["plan"]  # 返回数组

        # --- fallback（模型没用函数调用时）---
        content = res["content"].strip()
        # 尝试找到首尾中括号
        l_br = content.find("[")
        r_br = content.rfind("]")
        if l_br == -1 or r_br == -1:
            raise ValueError(f"LLM 未返回 JSON 数组，得到：{content[:120]}...")
        return json.loads(content[l_br:r_br + 1])

    def next_action(self, goal: str, last_res: str,
                    obs: Observation, hist_tail: List[str]) -> Dict:
        """
        单步 ReAct：要求 LLM 输出单条 JSON（依旧可用 function-call）
        """
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
            return json.loads(args_json)  # 单条 action dict
        # ---- 回退：模型直接用文本返回 ----
        content = (res["content"] or "").strip()

        # 若为空 / 仅空白：默认任务已完成
        if not content:
            return {"action": "finish"}

        # 若不是以 { 或 [ 开头，也视作结束（例如 "DONE"、"已完成"）
        if content[0] not in "{[":
            return {"action": "finish"}

        # 真正 JSON 才解析
        return json.loads(content)

    # ---------------- 内部工具 ----------------
    def _chat(self, messages,
              use_schema: bool = False,     # 已弃用，可保持兼容
              extra_tools: List[Dict] | None = None):
        """
        extra_tools：传入自定义 function-call 列表（如 return_plan / action）
        """
        tools = extra_tools
        return self.provider.chat(
            messages=messages,
            temperature=self.temperature,
            tools=tools
        )

    def _build_messages(self, goal, obs, stage,
                        last_result=None, history_tail=None):
        # ========== system prompt ==========
        ALLOWED = "move | click | click_img | type | hotkey | focus_window | sleep | finish"
        # llm_client.py – 创建 ACTION_SCHEMA 后加
        ALLOWED_HOTKEYS = [
            ["ctrl", "s"], ["ctrl", "o"], ["alt", "f4"]
        ]

        sys = (
            "你只能调用下列动作：move | click | click_img | type | hotkey | "
            "focus_window | sleep | finish。"
            "hotkey 仅允许组合键：Ctrl+S / Ctrl+O / Alt+F4。"
        )

        if self.mode == "text":
            sys += "你无法查看屏幕截图，只能根据窗口标题和历史日志推断。"
        system = {"role": "system", "content": sys}

        # ========== user / assistant ==========
        if stage == "plan":
            return [
                system,
                {"role": "user",
                 "content": f"任务目标：{goal}。\n请直接调用函数 `return_plan`，"
                            "返回一个有序动作数组完成任务。"},
                self._obs_msg(obs)
            ]

        tail = "\n".join(history_tail[-8:]) if history_tail else ""
        return [
            system,
            {"role": "assistant", "content": tail},
            {"role": "user",
             "content": f"目标：{goal}\n上一步结果：{last_result}\n"
                        "请直接调用函数 `action` 返回下一条原子动作 JSON。"},
            self._obs_msg(obs)
        ]

    def _obs_msg(self, obs: Observation):
        if self.mode == "vision":
            return obs.as_vision_message("(当前截图)")
        return obs.as_text_message()

