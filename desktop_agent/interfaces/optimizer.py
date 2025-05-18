from abc import ABC, abstractmethod
from typing import List, Dict


class IOptimizer(ABC):
    @abstractmethod
    def generate_suggestions(self, errors: List[Dict]) -> List[Dict]:
        """根据错误生成优化建议"""
        pass

    @abstractmethod
    def apply_optimizations(self, suggestions: List[Dict]) -> bool:
        """应用优化建议"""
        pass