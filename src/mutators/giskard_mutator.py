"""Giskard：扫被测 Agent，不改种子句子。

换智能体改 config.giskard.description + api.url。
LangTest / TextAttack 才走 samples.yaml。
"""
import asyncio
import os

from .base import BaseMutator


class GiskardMutator(BaseMutator):
    """保留类名给旧 import；generate() 不再对种子做变异。"""

    name = "giskard"

    def __init__(self, config=None):
        self.config = config or {}

    def generate(self, original_inputs: list[str], num_per_type: int = 5) -> list[dict]:
        raise RuntimeError("Giskard 不变异种子。请走 GiskardMutator.scan(runner)。")

    def scan(self, runner) -> list[dict]:
        cfg = self.config.get("giskard") or {}
        description = (cfg.get("description") or "").strip()
        if not description:
            print("[Giskard] 请在 config.yaml 填写 giskard.description（这个智能体是干什么的）。扫的是 Agent，不是种子。")
            return []
        try:
            return asyncio.run(self._scan_new(runner, cfg, description))
        except ImportError:
            print("[Giskard] 未安装新版 scan，尝试旧版 giskard.scan(Model)…")
            print('         pip install "giskard[scan,openai]"')
        except Exception as e:
            print(f"[Giskard] 新版 scan 失败，尝试旧版：{e}")
        return self._scan_legacy(runner, description)

    async def _scan_new(self, runner, cfg: dict, description: str) -> list[dict]:
        from giskard.scan import vulnerability_scan, quality_scan

        _configure_llm(self.config.get("llm_judge") or {})
        target = _make_target(runner)
        langs = cfg.get("languages") or ["zh"]
        max_scenarios = int(cfg.get("max_scenarios") or 8)
        kind = (cfg.get("kind") or "vulnerability").lower()
        kwargs = {
            "target": target,
            "description": description,
            "languages": langs,
            "max_scenarios": max_scenarios,
        }
        mode = cfg.get("target_mode") or "singleturn"
        try:
            kwargs["target_mode"] = mode
        except TypeError:
            pass

        scan_fn = quality_scan if kind == "quality" else vulnerability_scan
        print(f"  [giskard] {kind} scan，最多 {max_scenarios} 个场景，target=被测 API")
        try:
            result = await scan_fn(**kwargs)
        except TypeError:
            kwargs.pop("target_mode", None)
            result = await scan_fn(**kwargs)
        return _rows_from_suite(result)

    def _scan_legacy(self, runner, description: str) -> list[dict]:
        try:
            import giskard
            import pandas as pd
        except ImportError:
            print("[Giskard] 未安装 giskard，跳过 Agent 扫描。")
            return []

        def predict(df):
            replies = []
            for q in df["text"]:
                try:
                    replies.append(runner.call_api(str(q)).get("reply") or "")
                except Exception as e:
                    replies.append(f"[error] {e}")
            return replies

        wrapped = giskard.Model(
            model=predict,
            model_type="text_generation",
            name="agent-under-test",
            description=description,
        )
        df = pd.DataFrame({"text": ["你好", "介绍一下你能做什么"]})
        dataset = giskard.Dataset(df=df, target=None)
        report = giskard.scan(wrapped, dataset)
        return _rows_from_legacy(report)


def _make_target(runner):
    def target(inputs):
        text = _to_text(inputs)
        resp = runner.call_api(text)
        return resp.get("reply") or ""

    return target


def _to_text(inputs) -> str:
    if inputs is None:
        return ""
    if isinstance(inputs, str):
        return inputs
    for attr in ("question", "message", "content", "text"):
        if hasattr(inputs, attr):
            val = getattr(inputs, attr)
            if isinstance(val, str):
                return val
    if isinstance(inputs, dict):
        for key in ("question", "message", "content", "text"):
            if inputs.get(key):
                return str(inputs[key])
    if isinstance(inputs, list) and inputs:
        last = inputs[-1]
        if isinstance(last, dict):
            return str(last.get("content") or last.get("message") or last)
        return _to_text(last)
    return str(inputs)


def _configure_llm(llm_cfg: dict):
    key = llm_cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
    base = llm_cfg.get("base_url") or os.environ.get("OPENAI_BASE_URL", "")
    model = llm_cfg.get("model") or "gpt-4"
    if key:
        os.environ.setdefault("OPENAI_API_KEY", str(key))
    if base:
        os.environ.setdefault("OPENAI_BASE_URL", str(base))
        os.environ.setdefault("OPENAI_API_BASE", str(base))
    if not key:
        print("[Giskard] 未配置 llm_judge.api_key，scan 生成场景可能失败。")
        return
    try:
        from giskard.checks import set_default_generator
        set_default_generator(f"openai/{model}")
    except Exception:
        pass
    try:
        import giskard.llm as gllm
        if hasattr(gllm, "configure"):
            gllm.configure("openai", provider="openai", api_key=key, base_url=base)
    except Exception:
        pass


def _rows_from_suite(suite_result) -> list[dict]:
    items = getattr(suite_result, "results", None) or []
    rows = []
    for item in items:
        name = str(getattr(item, "name", None) or getattr(item, "scenario_name", None) or "scenario")
        passed = getattr(item, "passed", None)
        if passed is None:
            status = str(getattr(item, "status", "")).lower()
            passed = status in ("pass", "passed", "ok", "success")
        prompt = _extract_attr(item, ("input", "inputs", "prompt", "message"))
        reply = _extract_attr(item, ("output", "outputs", "reply", "response"))
        reason = getattr(item, "reason", None) or getattr(item, "error", None)
        rows.append({
            "original": name,
            "mutated": prompt or name,
            "mutation_type": str(getattr(item, "category", None) or "scan"),
            "mutator": "giskard",
            "status_code": 200 if passed else 0,
            "reply": reply,
            "error": None if passed else str(reason or "giskard check failed"),
        })
    if not rows and suite_result is not None:
        rows.append({
            "original": "giskard_scan",
            "mutated": "see console report",
            "mutation_type": "scan",
            "mutator": "giskard",
            "status_code": 200,
            "reply": str(getattr(suite_result, "pass_rate", suite_result)),
            "error": None,
        })
    return rows


def _rows_from_legacy(report) -> list[dict]:
    issues = getattr(report, "issues", None) or []
    rows = []
    for issue in issues:
        rows.append({
            "original": str(getattr(issue, "description", None) or getattr(issue, "name", "issue")),
            "mutated": str(getattr(issue, "examples", None) or ""),
            "mutation_type": str(getattr(issue, "taxonomy", None) or "scan"),
            "mutator": "giskard",
            "status_code": 0,
            "reply": str(getattr(issue, "slicing_fn", None) or ""),
            "error": str(issue),
        })
    if not rows:
        rows.append({
            "original": "giskard_scan",
            "mutated": "legacy scan finished",
            "mutation_type": "scan",
            "mutator": "giskard",
            "status_code": 200,
            "reply": str(report),
            "error": None,
        })
    return rows


def _extract_attr(obj, names) -> str:
    for name in names:
        val = getattr(obj, name, None)
        if val is None and isinstance(obj, dict):
            val = obj.get(name)
        if val is None:
            continue
        text = _to_text(val)
        if text:
            return text
    return ""
