"""中文变问法：近义词、同音字、删字、邻字对调。任意种子，不写死约课词表。"""
from .base import BaseMutator


class NlpcdaMutator(BaseMutator):
    name = "nlpcda"

    def __init__(self, config=None):
        self.config = config or {}

    def generate(self, original_inputs: list[str], num_per_type: int = 5) -> list[dict]:
        # create_num 含原文，多要 1 条再丢掉原文
        create_num = max(2, int(num_per_type) + 1)
        try:
            ops = _load_ops(create_num)
        except ImportError:
            print("[提示] 未安装 nlpcda，跳过中文变问法。pip install nlpcda")
            return []

        results = []
        for text in original_inputs:
            for kind, factory in ops:
                try:
                    variants = _as_list(factory().replace(text))
                except Exception as e:
                    print(f"[nlpcda/{kind}] 跳过：{e}")
                    continue
                seen = {text}
                for v in variants:
                    if not v or v in seen:
                        continue
                    seen.add(v)
                    results.append({
                        "original": text,
                        "mutated": v,
                        "mutation_type": kind,
                        "mutator": self.name,
                    })
                    if len(seen) - 1 >= num_per_type:
                        break
        return results


def _load_ops(create_num: int) -> list:
    from nlpcda import Homophone, RandomDeleteChar, Similarword

    ops = [
        ("similar_word", lambda: Similarword(create_num=create_num, change_rate=0.4)),
        ("homophone", lambda: Homophone(create_num=create_num, change_rate=0.1)),
        ("delete_char", lambda: RandomDeleteChar(create_num=create_num, change_rate=0.3)),
    ]
    try:
        from nlpcda import CharPositionExchange
        ops.append((
            "char_swap",
            lambda: CharPositionExchange(create_num=create_num, change_rate=0.3, char_gram=2),
        ))
    except ImportError:
        pass
    try:
        from nlpcda import EquivalentChar
        ops.append((
            "equivalent_num",
            lambda: EquivalentChar(create_num=create_num, change_rate=0.8),
        ))
    except ImportError:
        pass
    return ops


def _as_list(rs) -> list[str]:
    if rs is None:
        return []
    if isinstance(rs, str):
        return [rs]
    return [str(x) for x in rs if x]
