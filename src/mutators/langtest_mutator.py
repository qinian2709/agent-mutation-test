"""用 LangTest 的 transform 扰动任意种子句子，不包装被测智能体。"""
from .base import BaseMutator
from .robust import RobustMutator


class LangTestMutator(BaseMutator):
    name = "langtest"

    def __init__(self, config=None):
        self.config = config or {}

    def generate(self, original_inputs: list[str], num_per_type: int = 5) -> list[dict]:
        try:
            results = self._from_langtest(original_inputs, num_per_type)
            if results:
                return results
            print("[LangTest] transform 未产出新句子，回退到通用字符扰动（不含业务词表）")
        except ImportError:
            print("[提示] 未安装 langtest，鲁棒变异回退到通用字符扰动。")
            print("       pip install langtest")
        except Exception as e:
            print(f"[LangTest] 调用失败，回退通用扰动：{e}")
        fallback = RobustMutator().generate(original_inputs, num_per_type=num_per_type)
        for item in fallback:
            item["mutator"] = self.name
        return fallback

    def _from_langtest(self, original_inputs: list[str], num_per_type: int) -> list[dict]:
        from langtest.transform import robustness as rb
        from langtest.utils.custom_types.sample import SequenceClassificationSample

        # 这些 transform 只改字符串，和业务词无关；换智能体只换 samples.yaml
        specs = [
            ("add_typo", rb.AddTypo, {"prob": 0.6, "count": 1}),
            ("uppercase", rb.UpperCase, {}),
            ("lowercase", rb.LowerCase, {}),
            ("add_punctuation", rb.AddPunctuation, {}),
            ("strip_punctuation", rb.StripPunctuation, {}),
            ("ocr_typo", rb.AddOcrTypo, {}),
            ("add_context", rb.AddContext, {}),
            ("add_newlines", rb.AddNewLines, {}),
        ]

        results = []
        per_input_cap = max(1, num_per_type)
        for text in original_inputs:
            got = 0
            for kind, cls, kwargs in specs:
                if got >= per_input_cap:
                    break
                mutated = _apply_transform(cls, text, SequenceClassificationSample, kwargs)
                if not mutated or mutated == text:
                    continue
                results.append({
                    "original": text,
                    "mutated": mutated,
                    "mutation_type": kind,
                    "mutator": self.name,
                })
                got += 1
        return results


def _apply_transform(cls, text: str, sample_cls, kwargs: dict) -> str:
    sample = sample_cls(original=text, test_case=text)
    try:
        out = cls.transform([sample], **kwargs)
    except TypeError:
        out = cls.transform([sample])
    if not out:
        return ""
    item = out[0]
    for attr in ("test_case", "original", "text"):
        val = getattr(item, attr, None)
        if isinstance(val, str) and val.strip():
            return val
    return ""
