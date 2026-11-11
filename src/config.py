"""配置加载模块。兼容 README 的 api.* 与旧稿 agent.*/test.* 两种写法。"""
import os
import yaml
from pathlib import Path


def load_config(config_path: str = "config.yaml", demo: bool = False) -> dict:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在：{config_path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    config = _normalize(config)

    config.setdefault("mutation", {})
    if demo:
        config["mutation"]["demo"] = True
    config["mutation"].setdefault("enabled", "all")
    config["mutation"].setdefault("num_per_type", 5)
    config["mutation"].setdefault("demo", False)
    is_demo = bool(config["mutation"].get("demo"))

    config.setdefault("api", {})
    api = config["api"]
    if not is_demo:
        for field in ("url", "method", "body_template"):
            if not api.get(field):
                raise ValueError(f"api 配置缺少必要字段：{field}")
    else:
        api.setdefault("url", "")
        api.setdefault("method", "POST")
        api.setdefault("body_template", '{\n  "message": "{{message}}"\n}')

    api.setdefault("headers", {})
    api.setdefault("timeout", 30)
    api.setdefault("response_path", "")
    if not any(k.lower() == "content-type" for k in api["headers"]):
        api["headers"]["Content-Type"] = "application/json"

    config.setdefault("report", {})
    config["report"].setdefault("output_file", "./reports/report.html")
    config["report"].setdefault("title", "Agent 变异测试报告")

    config.setdefault("giskard", {})
    config["giskard"].setdefault("description", "")
    config["giskard"].setdefault("languages", ["zh"])
    config["giskard"].setdefault("max_scenarios", 8)
    config["giskard"].setdefault("kind", "vulnerability")
    config["giskard"].setdefault("target_mode", "singleturn")

    return config


def _normalize(config: dict) -> dict:
    """把 agent/test 旧字段折成代码使用的 api/mutation/report。"""
    if "api" not in config and "agent" in config:
        agent = config["agent"] or {}
        headers = {"Content-Type": "application/json"}
        api_key = agent.get("api_key") or os.environ.get("AGENT_API_KEY", "")
        if api_key and api_key not in ("your-api-key", "sk-xxx"):
            headers["Authorization"] = f"Bearer {api_key}"
        config["api"] = {
            "url": agent.get("url", ""),
            "method": agent.get("method", "POST"),
            "headers": headers,
            "body_template": agent.get("body_template") or '{\n  "message": "{{message}}"\n}',
            "timeout": agent.get("timeout", 30),
            "response_path": agent.get("response_path") or "reply",
        }

    if "mutation" not in config and "test" in config:
        test = config["test"] or {}
        config["mutation"] = {
            "enabled": test.get("mutator_types") or test.get("enabled") or "all",
            "num_per_type": test.get("num_mutations") or test.get("num_per_type") or 5,
        }
        output_dir = test.get("output_dir", "./reports")
        config.setdefault("report", {})
        config["report"].setdefault("output_file", str(Path(output_dir) / "report.html"))

    return config


def load_samples(samples_path: str = "inputs/samples.yaml") -> list[str]:
    path = Path(samples_path)
    if not path.exists():
        raise FileNotFoundError(f"输入文件不存在：{samples_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "samples" not in data:
        raise ValueError("输入文件缺少 'samples' 字段")

    return [s for s in data["samples"] if str(s).strip()]
