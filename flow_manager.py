from observer import Observation
from executor import Executor
from llm_client import LLMClient


class FlowManager:
    def __init__(self, goal: str,
                 mode="vision",
                 vendor="openai",
                 model=None,
                 provider_kwargs=None):
        self.goal = goal
        self.llm = LLMClient(mode, vendor, model, provider_kwargs)
        self.exec = Executor()
        self.hist = []

    def normalize_hotkeys(self, cmd):
        """规范化热键参数，处理两种格式"""
        if cmd.get("action") == "hotkey" and "args" in cmd:
            args = cmd["args"]
            if "key" in args and isinstance(args["key"], str):
                # 转换格式：'Ctrl+S' -> ['Ctrl', 'S']
                args["keys"] = args["key"].split("+")
                del args["key"]
            elif "keys" in args and isinstance(args["keys"], str):
                # 转换格式：'Ctrl,S' -> ['Ctrl', 'S']
                args["keys"] = args["keys"].split(",")

            if "keys" in args:
                # 确保keys是列表并转为小写比较
                args["_original_keys"] = args["keys"] if isinstance(args["keys"], list) else [args["keys"]]
                args["keys"] = [k.lower() for k in args["_original_keys"]]
        return cmd

    def validate_command(self, cmd):
        """验证命令参数完整性"""
        if not isinstance(cmd, dict) or "action" not in cmd:
            return False

        action = cmd["action"]
        args = cmd.get("args", {})

        # 动作特定验证
        if action == "click":
            if "x" not in args or "y" not in args:
                print("警告: 点击动作缺少坐标，将使用当前位置")
        elif action == "hotkey":
            if "keys" not in args and "key" not in args:
                return False

        return True

    def run(self, max_steps=40):
        obs = Observation.capture()
        plan = self.llm.get_plan(self.goal, obs)
        step = 0

        while step < max_steps and plan:
            cmd = self.normalize_hotkeys(plan.pop(0))
            print(f"准备执行命令: {cmd}")  # 调试日志

            if not self.validate_command(cmd):
                print(f"无效命令: {cmd}")
                continue
            try:
                result = self.exec.dispatch(cmd)
                self.hist.append(f"{step}:{cmd}->{result}")
                print(self.hist[-1])

                if result == "FINISH":
                    print("🎉 任务完成")
                    return

                obs = Observation.capture()
                if not plan or result.startswith("ERROR"):
                    new_cmd = self.llm.next_action(self.goal, result, obs, self.hist)
                    if new_cmd.get("action") == "finish":
                        print("🎉 任务完成")
                        return
                    plan.insert(0, self.normalize_hotkeys(new_cmd))

            except ValueError as e:
                print(f"命令执行失败: {e}")
                # 尝试让LLM重新生成命令
                obs = Observation.capture()
                new_cmd = self.llm.next_action(
                    self.goal,
                    f"前一个命令失败: {e}",
                    obs,
                    self.hist
                )
                plan.insert(0, self.normalize_hotkeys(new_cmd))

            step += 1

        print("❌ 未完成或达到步数上限")