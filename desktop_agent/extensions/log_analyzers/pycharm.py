from .base import BaseLogAnalyzer
from pathlib import Path
import os
from typing import Optional, List, Dict

class PyCharmLogAnalyzer(BaseLogAnalyzer):
    def __init__(self, log_source: Optional[str] = None):
        super().__init__(log_source)
        self.log_dir = self._find_log_dir()

    def _find_log_dir(self) -> Path:
        """查找PyCharm日志目录"""
        if self.log_source:
            return Path(self.log_source)

        possible_locations = [
            os.path.join(os.getenv("APPDATA", ""), "JetBrains", "PyCharm*", "log"),
            os.path.join(Path.home(), ".cache", "JetBrains", "PyCharm*", "log"),
            os.path.join(Path.home(), "Library", "Logs", "JetBrains", "PyCharm*")
        ]
        return super()._find_log_dir(possible_locations)

    def analyze(self) -> List[Dict]:
        """分析PyCharm日志"""
        all_errors = []
        for log_file in self.log_dir.glob("*.log"):
            all_errors.extend(self._parse_log_file(log_file))
        return all_errors

    def get_source_name(self) -> str:
        return "pycharm"