"""请求执行器"""
import requests
import json
from src.config import load_config


class Runner:
    """执行变异用例并收集响应"""

    def __init__(self, config="config.yaml"):
        if isinstance(config, dict):
            self.config = config
        else:
            self.config = load_config(config)
        self.api = self.config.get("api") or {}

    def call_api(self, message: str) -> dict:
        """
        调用被测 API

        Args:
            message: 要发送的消息

        Returns:
            包含 status_code, raw, reply 的字典
        """
        body = self._build_body(message)

        # 发送请求
        resp = requests.request(
            method=self.api["method"],
            url=self.api["url"],
            headers=self.api["headers"],
            json=body,
            timeout=self.api["timeout"]
        )

        # 解析响应
        try:
            data = resp.json()
        except:
            data = {"text": resp.text}

        return {
            "status_code": resp.status_code,
            "raw": data,
            "reply": self._extract_reply(data)
        }

    def _extract_reply(self, data: dict) -> str:
        """
        按 response_path 从响应中提取回复文本

        支持的路径格式：
        - "choices[0].message.content"
        - "result"
        - "data.text"
        """
        path = self.api.get("response_path", "")
        if not path:
            return str(data)

        # 解析路径
        current = data
        parts = path.replace("]", "").split("[")

        for part in parts:
            if not part:
                continue

            # 处理嵌套键（如 "message.content"）
            keys = part.split(".")
            for key in keys:
                if isinstance(current, dict):
                    current = current.get(key, "")
                elif isinstance(current, list) and key.isdigit():
                    idx = int(key)
                    current = current[idx] if idx < len(current) else ""
                else:
                    return ""

        return str(current) if current else ""

    def _build_body(self, message: str) -> dict:
        """把 {{message}} 填进 JSON 模板，避免注入文案里的引号把 body 弄坏。"""
        raw = self.api["body_template"]
        token = "__MUT_MSG__"
        try:
            parsed = json.loads(raw.replace("{{message}}", token))
        except json.JSONDecodeError:
            escaped = json.dumps(message, ensure_ascii=False)[1:-1]
            return json.loads(raw.replace("{{message}}", escaped))

        def fill(obj):
            if obj == token:
                return message
            if isinstance(obj, dict):
                return {k: fill(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [fill(x) for x in obj]
            if isinstance(obj, str) and token in obj:
                return obj.replace(token, message)
            return obj

        return fill(parsed)

    def run(self, mutations: list[dict], demo: bool = False) -> list[dict]:
        """
        批量执行变异用例。demo=True 时只打印变异、不打 API，状态/回复为空。
        """
        if demo:
            return self._demo_results(mutations)

        results = []
        total = len(mutations)

        print(f"\n开始执行 {total} 个变异用例...")

        for i, mut in enumerate(mutations, 1):
            mutated = mut.get("mutated") or ""
            print(f"[{i}/{total}] {mut.get('mutator')} - {mut.get('mutation_type')}: {mutated[:50]}...")

            try:
                resp = self.call_api(mut["mutated"])
                results.append({
                    **mut,
                    "status_code": resp["status_code"],
                    "reply": resp["reply"],
                    "error": None
                })
            except Exception as e:
                results.append({
                    **mut,
                    "status_code": 0,
                    "reply": "",
                    "error": str(e)
                })

        print(f"\n执行完成：成功 {sum(1 for r in results if r['status_code'] == 200)}/{total}")

        return results

    def _demo_results(self, mutations: list[dict]) -> list[dict]:
        total = len(mutations)
        print(f"\n演示模式：只展示 {total} 条变异，不发起 API 请求")
        results = []
        for mut in mutations:
            original = mut.get("original") or ""
            mutated = mut.get("mutated") or ""
            print(f"[{mut.get('mutator')}/{mut.get('mutation_type')}]")
            print(f"  原：{original}")
            print(f"  变：{mutated}")
            results.append({
                "original": original,
                "mutated": mutated,
                "mutation_type": mut.get("mutation_type") or "",
                "mutator": mut.get("mutator") or "",
                "status_code": None,
                "reply": "",
                "error": None,
            })
        return results
