from .base import BaseLogAnalyzer
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict

class ExcelLogAnalyzer(BaseLogAnalyzer):
    def __init__(self, log_source: Optional[str] = None):
        super().__init__(log_source)
        self.supported_formats = ['.xlsx', '.xls', '.csv']

    def analyze(self) -> List[Dict]:
        """分析Excel日志文件"""
        if not self.log_source:
            raise ValueError("Excel分析器需要明确指定日志文件路径")

        path = Path(self.log_source)
        if path.suffix not in self.supported_formats:
            raise ValueError(f"不支持的文件格式: {path.suffix}")

        try:
            if path.suffix == '.csv':
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)

            # 假设错误在'Error'列中
            if 'Error' not in df.columns:
                return []

            return [{
                'file': str(path),
                'error': row['Error'],
                'timestamp': row.get('Timestamp', ''),
                'source': self.get_source_name()
            } for _, row in df.iterrows() if pd.notna(row['Error'])]

        except Exception as e:
            print(f"解析Excel日志失败: {e}")
            return []

    def get_source_name(self) -> str:
        return "excel"