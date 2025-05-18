from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from pathlib import Path


class ILogAnalyzer(ABC):
    @abstractmethod
    def __init__(self, log_source: Optional[str] = None):
        """初始化分析器"""
        pass

    @abstractmethod
    def analyze(self) -> List[Dict]:
        """分析日志并返回错误列表"""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """获取日志源名称"""
        pass