# desktop_agent/extensions/optimizers/llm_opt.py

from desktop_agent.interfaces.optimizer import IOptimizer
from typing import List, Dict
import json


class LLMOptimizer(IOptimizer):
    def __init__(self, llm_client):
        self.llm = llm_client

    DIFF_PROMPT = (
        "请针对下列 Python 错误生成 **git unified diff** 补丁，"
        "只修改触发错误的文件；不包含解释文字。\n\n错误:\n{error}\n"
    )

    def generate_suggestions(self, errors: List[Dict]) -> List[Dict]:
        suggestions = []
        for err in errors:
            prompt = self.DIFF_PROMPT.format(
                error=json.dumps(err, ensure_ascii=False, indent=2))
            rsp = self.llm._chat([{"role":"user","content":prompt}])
            suggestions.append({
                "error": err,
                "diff":  rsp["content"].strip(),
                "source": err["source"]
            })
        return suggestions

    def apply_optimizations(self, suggestions: List[Dict]) -> bool:
        import subprocess, tempfile, pathlib, shutil, textwrap
        success = True
        for s in suggestions:
            diff_text = s["diff"]
            if not diff_text.startswith("---"):
                print("非 diff 补丁，跳过"); continue

            # 写入临时补丁文件
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".patch") as tmp:
                tmp.write(diff_text)
                patch_path = tmp.name

            # 为目标文件做 *.orig 备份
            lines = diff_text.splitlines()
            orig_file = lines[0].split()[-1].lstrip("a/")
            if pathlib.Path(orig_file).exists():
                shutil.copy(orig_file, orig_file + ".orig")

            # 应用补丁
            try:
                subprocess.run(["git","apply",patch_path], check=True)
                subprocess.run(["git","add",orig_file], check=True)
                subprocess.run(["git","commit","-m","auto-fix by LLM"], check=True)
                print(f"✓ 已应用补丁并提交: {orig_file}")
            except subprocess.CalledProcessError as e:
                print(f"❌ git apply 失败: {e}")
                success = False
        return success
