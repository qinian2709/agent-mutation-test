import pytest

from src.config import _normalize
from src.mutators.robust import RobustMutator
from src.mutators.security import SecurityMutator


def test_old_agent_schema_normalizes():
    cfg = _normalize({
        "agent": {"url": "http://example/chat", "timeout": 10},
        "test": {"mutator_types": "all", "num_mutations": 3, "output_dir": "./out"},
    })
    assert cfg["api"]["url"] == "http://example/chat"
    assert cfg["api"]["method"] == "POST"
    assert "{{message}}" in cfg["api"]["body_template"]
    assert cfg["mutation"]["enabled"] == "all"
    assert cfg["mutation"]["num_per_type"] == 3


def test_enabled_all_keeps_nlpcda_textattack_giskard():
    from src.main import _enabled_set
    assert _enabled_set("all") == {"langtest", "nlpcda", "textattack", "giskard"}
    assert _enabled_set("textattack") == {"textattack"}
    assert _enabled_set("nlpcda") == {"nlpcda"}
    assert _enabled_set("giskard") == {"giskard"}
    assert _enabled_set("security") == {"giskard"}


def test_nlpcda_skips_original():
    from src.mutators.nlpcda_mutator import _as_list
    assert _as_list(None) == []
    assert _as_list("a") == ["a"]
    assert _as_list(["a", "b"]) == ["a", "b"]


def test_nlpcda_mutates_chinese_seed():
    pytest.importorskip("nlpcda")
    from src.mutators.nlpcda_mutator import NlpcdaMutator

    seed = "帮我给张三排李老师的课，明天下午3点"
    rows = NlpcdaMutator().generate([seed], num_per_type=2)
    assert rows, "nlpcda 应对中文种子产出变问法"
    assert all(r["mutator"] == "nlpcda" for r in rows)
    assert all(r["original"] == seed for r in rows)
    assert all(r["mutated"] != seed for r in rows)
    kinds = {r["mutation_type"] for r in rows}
    assert kinds & {"similar_word", "homophone", "delete_char", "char_swap", "equivalent_num"}


def test_demo_config_allows_empty_api(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("mutation:\n  demo: true\n", encoding="utf-8")
    from src.config import load_config
    loaded = load_config(str(cfg), demo=True)
    assert loaded["mutation"]["demo"] is True
    assert loaded["api"]["url"] == ""


def test_demo_run_does_not_call_api():
    from src.runner import Runner
    runner = Runner({"api": {}})

    def boom(*_a, **_k):
        raise AssertionError("演示模式不得请求 API")

    runner.call_api = boom
    out = runner.run(
        [{"original": "帮我排课", "mutated": "帮我约课", "mutation_type": "similar_word", "mutator": "nlpcda"}],
        demo=True,
    )
    assert len(out) == 1
    assert out[0]["status_code"] is None
    assert out[0]["reply"] == ""
    assert out[0]["error"] is None


def test_reporter_allows_empty_fields(tmp_path):
    from src.reporter import Reporter
    out = tmp_path / "demo.html"
    Reporter({"report": {"title": "t"}}).generate(
        [
            {
                "mutator": "nlpcda",
                "mutation_type": "similar_word",
                "original": "帮我给张三排课",
                "mutated": "帮我给张三约课",
                "status_code": None,
                "reply": "",
                "error": None,
            },
            {},
        ],
        str(out),
        demo=True,
    )
    html = out.read_text(encoding="utf-8")
    assert "演示模式" in html
    assert "未请求" in html
    assert "帮我给张三约课" in html


def test_reporter_empty_results_ok(tmp_path):
    from src.reporter import Reporter
    out = tmp_path / "empty.html"
    Reporter({"report": {}}).generate([], str(out), demo=True)
    html = out.read_text(encoding="utf-8")
    assert "暂无测试数据" in html
    assert "演示模式允许为空" in html


def test_mutators_are_seed_agnostic():
    seeds = ["查询订单 ORD-20261103 的发货状态"]
    robust = RobustMutator().generate(seeds, num_per_type=4)
    security = SecurityMutator().generate(seeds, num_per_type=2)
    assert len(robust) >= 1
    assert all(r["original"] == seeds[0] for r in robust + security)
    assert all(r["mutated"] != r["original"] for r in robust)
    assert all(seeds[0] in r["mutated"] for r in security)
