"""英文变问法（WordNet / EDA / CheckList）。未安装或中文无同义词时自动跳过。"""
from .base import BaseMutator


class TextAttackMutator(BaseMutator):
    name = "textattack"

    def __init__(self, config=None):
        self.config = config or {}

    def generate(self, original_inputs: list[str], num_per_type: int = 5) -> list[dict]:
        try:
            from textattack.augmentation import (
                WordNetAugmenter,
                EasyDataAugmenter,
                CheckListAugmenter,
            )
        except ImportError:
            print("[提示] TextAttack 未安装，跳过英文变问法。pip install textattack")
            return []

        n = max(1, min(num_per_type, 3))
        builders = [
            ("synonym", lambda: WordNetAugmenter(transformations_per_example=n)),
            ("eda", lambda: EasyDataAugmenter(transformations_per_example=n)),
            ("checklist", lambda: CheckListAugmenter(transformations_per_example=n)),
        ]

        results = []
        for text in original_inputs:
            for aug_name, factory in builders:
                try:
                    augmenter = factory()
                    variants = _augment(augmenter, text, n)
                except Exception as e:
                    print(f"[TextAttack/{aug_name}] 跳过：{e}")
                    continue
                for v in variants:
                    if not v or v == text:
                        continue
                    results.append({
                        "original": text,
                        "mutated": v,
                        "mutation_type": aug_name,
                        "mutator": self.name,
                    })
        return results


def _augment(augmenter, text: str, n: int) -> list[str]:
    out = None
    for kwargs in ({}, {"n": n}, {"num_augmentations": n}):
        try:
            out = augmenter.augment(text, **kwargs) if kwargs else augmenter.augment(text)
            break
        except TypeError:
            continue
    if out is None:
        return []
    if isinstance(out, str):
        return [out]
    return list(out)[:n]
