"""LangTest 不可用时的通用字符扰动。不含任何业务同义词，任意中文/英文种子都能用。"""
import random
import re
from .base import BaseMutator


class RobustMutator(BaseMutator):
    name = "robust"

    def __init__(self, config=None):
        self.config = config or {}

    def generate(self, original_inputs: list[str], num_per_type: int = 5) -> list[dict]:
        results = []
        for text in original_inputs:
            seen = {text}
            for mutated, kind in self._variants(text, num_per_type):
                if mutated in seen or not mutated.strip():
                    continue
                seen.add(mutated)
                results.append({
                    "original": text,
                    "mutated": mutated,
                    "mutation_type": kind,
                    "mutator": self.name,
                })
        return results

    def _variants(self, text: str, limit: int) -> list[tuple[str, str]]:
        rng = random.Random(sum(map(ord, text)) % 2**32)
        ops = [
            ("char_swap", self._swap_adjacent),
            ("char_drop", self._drop_char),
            ("char_repeat", self._repeat_char),
            ("spacing", self._spacing),
            ("punct", self._punct),
        ]
        rng.shuffle(ops)
        out = []
        for kind, fn in ops:
            if len(out) >= limit:
                break
            mutated = fn(text, rng)
            if mutated and mutated != text:
                out.append((mutated, kind))
        return out

    def _editable_indices(self, text: str) -> list[int]:
        return [i for i, ch in enumerate(text) if not ch.isspace()]

    def _swap_adjacent(self, text: str, rng: random.Random) -> str:
        idx = self._editable_indices(text)
        if len(idx) < 2:
            return text
        i = rng.choice(idx[:-1])
        chars = list(text)
        if chars[i].isspace() or chars[i + 1].isspace():
            return text
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
        return "".join(chars)

    def _drop_char(self, text: str, rng: random.Random) -> str:
        idx = self._editable_indices(text)
        if len(idx) < 4:
            return text
        i = rng.choice(idx[1:-1])
        return text[:i] + text[i + 1:]

    def _repeat_char(self, text: str, rng: random.Random) -> str:
        idx = self._editable_indices(text)
        if not idx:
            return text
        i = rng.choice(idx)
        return text[:i] + text[i] + text[i:]

    def _spacing(self, text: str, rng: random.Random) -> str:
        idx = self._editable_indices(text)
        if len(idx) < 3:
            return re.sub(r"\s+", "  ", text)
        i = rng.choice(idx)
        return text[:i] + " " + text[i:]

    def _punct(self, text: str, rng: random.Random) -> str:
        extra = rng.choice(["？", "!", "...", "。"])
        if text.endswith(extra):
            return extra + text
        return text + extra
