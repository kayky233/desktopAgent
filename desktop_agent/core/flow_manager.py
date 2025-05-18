import os
import sys
from typing import List, Optional

from desktop_agent.core.executor import Executor
from desktop_agent.core.llm_client import LLMClient
from desktop_agent.core.observer import Observation
from desktop_agent.interfaces.analyzer import ILogAnalyzer
from desktop_agent.interfaces.optimizer import IOptimizer
from desktop_agent.extensions.log_analyzers import PyCharmLogAnalyzer, ExcelLogAnalyzer
from desktop_agent.extensions.optimizers import LLMOptimizer
import traceback
from desktop_agent.extensions.log_analyzers.pycharm import PyCharmLogAnalyzer
from desktop_agent.extensions.log_analyzers.traceback import TracebackAnalyzer
from desktop_agent.extensions.optimizers.llm_opt import LLMOptimizer


class FlowManager:
    def __init__(self, goal: str,
                 mode="vision",
                 vendor="openai",
                 model=None,
                 provider_kwargs=None,
                 log_analyzers: Optional[List[str]] = None,
                 optimizers: Optional[List[str]] = None):

        self.goal = goal
        self.llm = LLMClient(mode, vendor, model, provider_kwargs)
        self.exec = Executor()
        self.hist = []

        # 初始化分析器和优化器
        self.log_analyzers = self._init_analyzers(log_analyzers)
        self.optimizers = self._init_optimizers(optimizers)
        self.optimizer = LLMOptimizer(self.llm)
        self.analyzers = [
            PyCharmLogAnalyzer(),  # IDE 日志
        ]

    def _init_analyzers(self, analyzer_names: Optional[List[str]]) -> List[ILogAnalyzer]:
        """初始化日志分析器"""
        analyzers = []
        if not analyzer_names:
            return analyzers

        for name in analyzer_names:
            try:
                if name == "pycharm":
                    analyzers.append(PyCharmLogAnalyzer())
                elif name == "excel":
                    analyzers.append(ExcelLogAnalyzer())
                # 可以添加更多分析器
            except Exception as e:
                print(f"初始化分析器 {name} 失败: {e}")
        return analyzers

    def _init_optimizers(self, optimizer_names: Optional[List[str]]) -> List[IOptimizer]:
        """初始化优化器"""
        optimizers = []
        if not optimizer_names:
            return optimizers

        for name in optimizer_names:
            try:
                if name == "llm":
                    optimizers.append(LLMOptimizer(self.llm))
                # 可以添加更多优化器
            except Exception as e:
                print(f"初始化优化器 {name} 失败: {e}")
        return optimizers

    def analyze_and_optimize(self):
        """执行日志分析和优化"""
        if not self.log_analyzers or not self.optimizers:
            return []

        all_errors = []
        for analyzer in self.log_analyzers:
            try:
                all_errors.extend(analyzer.analyze())
            except Exception as e:
                print(f"日志分析失败({analyzer.get_source_name()}): {e}")

        suggestions = []
        for optimizer in self.optimizers:
            try:
                suggestions.extend(optimizer.generate_suggestions(all_errors))
            except Exception as e:
                print(f"优化建议生成失败: {e}")

        return suggestions

    # ... 其余原有方法保持不变 ...

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


            except Exception as e:

                tb_str = traceback.format_exc()

                print(f"执行失败: {e}\n{tb_str}")

                # 1) Traceback 实时分析

                errors = TracebackAnalyzer(tb_str).analyze()

                # 2) IDE 日志追加

                for ana in self.analyzers:

                    try:

                        errors += ana.analyze()

                    except FileNotFoundError as fe:

                        print(f"初始化分析器 {ana.get_source_name()} 失败: {fe}")

                if not errors:
                    print("未提取到结构化错误，终止。")

                    return

                # 3) 让 LLM 生成补丁

                suggestions = self.optimizer.generate_suggestions(errors)

                if self.optimizer.apply_optimizations(suggestions):

                    print("已应用补丁，重新执行脚本…")

                    os.execv(sys.executable, [sys.executable] + sys.argv)  # 重启进程

                else:

                    print("补丁应用失败，终止。")

                    return

            step += 1

        print("❌ 未完成或达到步数上限")