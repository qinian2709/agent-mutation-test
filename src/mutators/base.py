"""变异器基类"""
from abc import ABC, abstractmethod


class BaseMutator(ABC):
    """变异器基类"""

    name: str = "base"

    @abstractmethod
    def generate(self, original_inputs: list[str], num_per_type: int = 5) -> list[dict]:
        """
        生成变异用例

        Args:
            original_inputs: 原始输入文本列表
            num_per_type: 每条原始输入、每种策略最多生成多少条

        Returns:
            变异用例列表，每个包含：
            - original: 原始输入
            - mutated: 变异后输入
            - mutation_type: 变异类型
            - mutator: 变异器名称
        """
        pass
