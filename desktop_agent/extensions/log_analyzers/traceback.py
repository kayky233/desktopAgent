from .base import BaseLogAnalyzer
import traceback, re
from typing import List, Dict

class TracebackAnalyzer(BaseLogAnalyzer):
    """
    直接从最近一次 try/except 的 traceback 字符串里提取错误信息
    用于 FlowManager 实时捕获，而非 IDE 日志
    """
    def __init__(self, tb_str: str):
        super().__init__(log_source=None)
        self.tb_str = tb_str

    def analyze(self) -> List[Dict]:
        pattern = re.compile(r'File "(.+?)", line (\d+), in (.*?)\n\s*(.*)')
        match = pattern.search(self.tb_str)
        if not match:
            return []
        file, line, func, code = match.groups()
        err_type_msg = self.tb_str.strip().splitlines()[-1]
        return [{
            "file": file,
            "line": int(line),
            "function": func,
            "code": code.strip(),
            "error": err_type_msg,
            "timestamp": "",
            "source": "traceback"
        }]
