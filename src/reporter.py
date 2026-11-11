"""报告生成器"""
from datetime import datetime
from pathlib import Path
from jinja2 import Template


REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f0f11;
    color: #e4e4e7;
    padding: 24px;
    line-height: 1.6;
  }
  h1 { font-size: 28px; margin-bottom: 8px; }
  .subtitle { color: #71717a; font-size: 14px; margin-bottom: 32px; }

  .summary {
    display: flex;
    gap: 24px;
    margin: 32px 0;
    flex-wrap: wrap;
  }
  .stat {
    background: #1a1a1f;
    padding: 20px 28px;
    border-radius: 12px;
    min-width: 140px;
  }
  .stat .num {
    font-size: 36px;
    font-weight: 700;
    color: #60a5fa;
  }
  .stat .label {
    color: #71717a;
    font-size: 13px;
    margin-top: 4px;
  }

  .group { margin: 40px 0; }
  .group-title {
    font-size: 20px;
    font-weight: 600;
    padding: 12px 0;
    border-bottom: 2px solid #2e2e36;
    margin-bottom: 16px;
  }
  .group-title .count {
    color: #71717a;
    font-size: 16px;
    font-weight: 400;
    margin-left: 8px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    background: #1a1a1f;
    border-radius: 8px;
    overflow: hidden;
  }
  th {
    background: #25252b;
    padding: 12px 16px;
    text-align: left;
    font-size: 13px;
    color: #a1a1aa;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  td {
    padding: 12px 16px;
    border-bottom: 1px solid #2e2e36;
    font-size: 14px;
    vertical-align: top;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover { background: #25252b; }

  .tag {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
  }
  .tag-langtest { background: #1e3a5f; color: #60a5fa; }
  .tag-nlpcda { background: #1e3a4a; color: #38bdf8; }
  .tag-textattack { background: #3b1f5e; color: #c084fc; }
  .tag-giskard { background: #1f4e3b; color: #34d399; }

  .status {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }
  .status-200 { background: #1f4e3b; color: #34d399; }
  .status-error { background: #4e1f1f; color: #f87171; }
  .status-skip { background: #3f3f46; color: #a1a1aa; }

  .banner-demo {
    background: #1e3a4a;
    color: #7dd3fc;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 24px;
  }

  .reply {
    color: #a1a1aa;
    font-size: 13px;
    max-width: 400px;
    word-break: break-all;
    line-height: 1.5;
  }
  .original {
    color: #52525b;
    font-size: 12px;
    font-style: italic;
  }
  .error {
    color: #f87171;
    font-size: 13px;
  }

  .empty {
    text-align: center;
    padding: 40px;
    color: #71717a;
  }
</style>
</head>
<body>

<h1>{{ title }}</h1>
<p class="subtitle">生成时间：{{ generated_at }}</p>
{% if demo %}
<p class="banner-demo">演示模式：只展示种子变异，未向 Agent API 发请求。状态 / 回复 / 错误都可以为空。</p>
{% endif %}

<div class="summary">
  <div class="stat">
    <div class="num">{{ total }}</div>
    <div class="label">总变异数</div>
  </div>
  <div class="stat">
    <div class="num" style="color: #34d399;">{{ success }}</div>
    <div class="label">请求成功</div>
  </div>
  <div class="stat">
    <div class="num" style="color: #f87171;">{{ failed }}</div>
    <div class="label">请求失败</div>
  </div>
  {% if demo or skipped %}
  <div class="stat">
    <div class="num" style="color: #a1a1aa;">{{ skipped }}</div>
    <div class="label">未请求</div>
  </div>
  {% endif %}
  <div class="stat">
    <div class="num" style="color: #c084fc;">{{ mutator_count }}</div>
    <div class="label">变异器数量</div>
  </div>
</div>

{% if not groups %}
<div class="empty">暂无测试数据{% if demo %}（演示模式允许为空）{% endif %}</div>
{% else %}

{% for group_name, items in groups.items() %}
<div class="group">
  <div class="group-title">
    {{ group_name }}
    <span class="count">({{ items|length }} 个)</span>
  </div>
  <table>
    <thead>
      <tr>
        <th style="width: 40px;">#</th>
        <th style="width: 100px;">变异器</th>
        <th style="width: 120px;">变异类型</th>
        <th>原始输入</th>
        <th>变异输入</th>
        <th style="width: 80px;">状态</th>
        <th>API 回复</th>
        <th style="width: 150px;">错误</th>
      </tr>
    </thead>
    <tbody>
      {% for item in items %}
      {% set orig = item.original if item.original else '' %}
      {% set mut = item.mutated if item.mutated else '' %}
      {% set reply = item.reply if item.reply else '' %}
      {% set code = item.status_code %}
      <tr>
        <td>{{ loop.index }}</td>
        <td><span class="tag tag-{{ item.mutator or 'unknown' }}">{{ item.mutator or '—' }}</span></td>
        <td>{{ item.mutation_type or '—' }}</td>
        <td class="original">{{ orig[:80] if orig else '—' }}{% if orig|length > 80 %}...{% endif %}</td>
        <td>{{ mut[:80] if mut else '—' }}{% if mut|length > 80 %}...{% endif %}</td>
        <td>
          {% if code is none %}
          <span class="status status-skip">未请求</span>
          {% elif code == 200 %}
          <span class="status status-200">{{ code }}</span>
          {% else %}
          <span class="status status-error">{{ code if code else 'ERR' }}</span>
          {% endif %}
        </td>
        <td class="reply">{{ reply[:300] if reply else '—' }}{% if reply|length > 300 %}...{% endif %}</td>
        <td class="error">{{ item.error or '—' }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endfor %}

{% endif %}

</body>
</html>
"""


def _normalize_row(r: dict) -> dict:
    r = r or {}
    return {
        "original": r.get("original") or "",
        "mutated": r.get("mutated") or "",
        "mutation_type": r.get("mutation_type") or "",
        "mutator": r.get("mutator") or "",
        "status_code": r.get("status_code"),
        "reply": r.get("reply") or "",
        "error": r.get("error"),
    }


class Reporter:
    """生成汇总报告"""

    def __init__(self, config: dict):
        self.config = config.get("report", {})

    def generate(self, results: list[dict], output_file: str, demo: bool = False):
        """生成 HTML 报告。demo 时允许状态码 / 回复为空，不把未请求算作失败。"""
        groups = {}
        rows = [_normalize_row(r) for r in results]
        for r in rows:
            key = f"{r['mutator'] or 'unknown'} - {r['mutation_type'] or 'unknown'}"
            groups.setdefault(key, []).append(r)

        total = len(rows)
        success = sum(1 for r in rows if r.get("status_code") == 200)
        skipped = sum(1 for r in rows if r.get("status_code") is None)
        failed = total - success - skipped
        mutators = {r.get("mutator") for r in rows if r.get("mutator")}
        mutator_count = len(mutators)

        title = self.config.get("title", "Agent 变异测试报告")
        if demo and "演示" not in title:
            title = f"{title}（演示模式）"

        template = Template(REPORT_TEMPLATE)
        html = template.render(
            title=title,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total=total,
            success=success,
            failed=failed,
            skipped=skipped,
            mutator_count=mutator_count,
            groups=groups,
            demo=demo,
        )

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"\n报告已生成：{output_file}")
        print(f"  总变异数：{total}")
        print(f"  请求成功：{success}")
        print(f"  请求失败：{failed}")
        if demo or skipped:
            print(f"  未请求：{skipped}")
        print(f"  变异器数：{mutator_count}")
