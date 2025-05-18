from desktop_agent.interfaces.analyzer import ILogAnalyzer
from pathlib import Path
import re
from datetime import datetime
from typing import Optional, List, Dict


class BaseLogAnalyzer(ILogAnalyzer):
    def __init__(self, log_source: Optional[str] = None):
        self.log_source = log_source
        self.error_patterns = [
            r"ERROR\s+-\s+(.*)",
            r"Exception:\s+(.*)",
            r"Traceback.*?\n(.*?)\n\n"
        ]

    def _find_log_dir(self, possible_locations: List[str]) -> Path:
        """查找日志目录"""
        for location in possible_locations:
            path = Path(location)
            if path.exists():
                return path
        raise FileNotFoundError(f"无法找到日志目录，尝试过: {possible_locations}")

    def _parse_log_file(self, file_path: Path) -> List[Dict]:
        """解析单个日志文件"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

                for pattern in self.error_patterns:
                    matches = re.finditer(pattern, content, re.DOTALL)
                    for match in matches:
                        error_msg = match.group(1).strip()
                        errors.append({
                            'file': str(file_path),
                            'error': error_msg,
                            'timestamp': datetime.fromtimestamp(
                                file_path.stat().st_mtime
                            ).isoformat(),
                            'source': self.get_source_name()
                        })
        except Exception as e:
            print(f"解析日志文件 {file_path} 失败: {e}")
        return errors

    def analyze(self) -> List[Dict]:
        """基础分析实现"""
        raise NotImplementedError("子类必须实现此方法")

    def get_source_name(self) -> str:
        """基础源名称"""
        return "base_log"