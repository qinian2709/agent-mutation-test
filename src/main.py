"""主入口：nlpcda/LangTest/TextAttack 变异种子并打 API；Giskard 直接扫被测 Agent。"""
import sys
import argparse
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_config, load_samples
from src.mutators import LangTestMutator, TextAttackMutator, NlpcdaMutator, GiskardMutator
from src.runner import Runner
from src.reporter import Reporter

_ALIASES = {"robust": "langtest", "security": "giskard"}


def _enabled_set(enabled) -> set:
    if enabled == "all":
        return {"langtest", "nlpcda", "textattack", "giskard"}
    key = _ALIASES.get(str(enabled), str(enabled))
    return {key}


def main():
    parser = argparse.ArgumentParser(description="Agent 变异测试框架")
    parser.add_argument("-o", "--open", action="store_true", help="测试完成后自动打开报告")
    parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("-i", "--inputs", default="inputs/samples.yaml", help="输入文件路径")
    parser.add_argument("--demo", action="store_true", help="只变异种子，不打 API，仍生成报告")
    args = parser.parse_args()

    print("=" * 60)
    print("Agent 测试框架  ·  变种子 / 扫 Agent 分开")
    print("=" * 60)

    print("\n[1/5] 加载配置...")
    config = load_config(args.config, demo=args.demo)
    enabled = _enabled_set(config["mutation"]["enabled"])
    demo = bool(config["mutation"].get("demo"))
    print(f"  API 地址：{config['api'].get('url') or '（演示模式可空）'}")
    print(f"  启用：{', '.join(sorted(enabled))}")
    if demo:
        print("  模式：演示（只变异，不请求 API）")

    need_seeds = bool(enabled & {"langtest", "nlpcda", "textattack", "robust"})
    samples = []
    if need_seeds:
        print("\n[2/5] 加载种子输入（LangTest / nlpcda / TextAttack）...")
        samples = load_samples(args.inputs)
        print(f"  {len(samples)} 条")
    else:
        print("\n[2/5] 仅 Giskard 扫描，不读种子文件")

    runner = Runner(config)
    results = []

    print("\n[3/5] 种子变异（中文 nlpcda / 英文 TextAttack / LangTest）...")
    num_per_type = int(config["mutation"].get("num_per_type") or 5)
    mutations = []
    for key, cls in (
        ("langtest", LangTestMutator),
        ("nlpcda", NlpcdaMutator),
        ("textattack", TextAttackMutator),
    ):
        if key not in enabled:
            continue
        mutator = cls(config)
        print(f"  [{mutator.name}]")
        mutations.extend(mutator.generate(samples, num_per_type=num_per_type))
    print(f"  变异用例 {len(mutations)} 条")

    print("\n[4/5] 执行...")
    if mutations:
        results.extend(runner.run(mutations, demo=demo))
    if "giskard" in enabled:
        if demo:
            print("  [giskard] 演示模式跳过（扫描会打真实 Agent）")
        else:
            print("  [giskard] 扫描被测 Agent（自己出场景，不改种子）")
            results.extend(GiskardMutator(config).scan(runner))

    if not results:
        if demo:
            print("\n[提示] 演示模式没有变异结果，仍生成空报告。")
        else:
            print("\n[警告] 没有任何结果。检查种子、nlpcda/langtest/textattack 安装，或 giskard.description。")
            sys.exit(0)

    print("\n[5/5] 生成报告...")
    output_file = config["report"]["output_file"]
    Reporter(config).generate(results, output_file, demo=demo)

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

    if args.open:
        report_path = Path(output_file).resolve()
        if report_path.exists():
            webbrowser.open(f"file://{report_path}")
            print("报告已打开")


if __name__ == "__main__":
    main()
