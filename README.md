# Agent 变异测试框架

对当前智能体的**每条**用户问法做变问法，再打 API；Giskard 另外扫 Agent。结果进同一份 HTML。先看回复对不对，后续再加 `code=0` 等断言。

各库做什么、一条种子会变成什么（含真实日志）见 **[docs/libraries.md](docs/libraries.md)**。

## 核心流程

```
samples.yaml 里的每一条种子              config.giskard.description
        │                                          │
        ▼                                          ▼
 nlpcda / TextAttack / LangTest              Giskard.scan(被测 API)
 每条种子各自变异（不是只改第一条）            自己出场景，不改种子
        │                                          │
        └──────────────┬───────────────────────────┘
                       ▼
                 同一份 HTML 报告
                       │
          --demo 时停在变异，不发 API
```

`inputs/samples.yaml` 有几条，就对几条分别变异。上次演示 6 条种子 → 136 条用例，报告「原始输入」列能看出对应哪条种子。只看一条时，yaml 里只留一句即可。

---

## 项目结构

```
agent-mutation-test/
├── README.md                 # 本文档
├── docs/libraries.md         # 各库说明 + 约课/查数变异案例
├── requirements.txt
├── config.yaml
├── src/
│   ├── main.py               # 入口（含 --demo）
│   ├── config.py
│   ├── runner.py             # 打 API；demo 时只填空结果
│   ├── reporter.py           # HTML；允许状态/回复为空
│   └── mutators/
│       ├── nlpcda_mutator.py
│       ├── textattack_mutator.py
│       ├── langtest_mutator.py
│       └── giskard_mutator.py
├── inputs/samples.yaml
└── reports/report.html
```

---

## 快速开始

```bash
pip install -r requirements.txt
```

1. 改 `inputs/samples.yaml`：换成**当前**智能体的真实问法（中英可混写，几条都会变异）。
2. 正式跑前改 `config.yaml` 的 `api.url`；Giskard 还要改 `giskard.description`。
3. 先看变异、不打接口：

```bash
python src/main.py --demo --open
```

4. 变异后请求被测 Agent：

```bash
python src/main.py --open
```

演示模式不发起 HTTP，报告里状态为「未请求」，回复可以为空。Giskard 在演示时跳过（扫描会打真实 Agent）。

---

## 命令行

| 参数 | 简写 | 说明 |
|------|------|------|
| `--demo` | | 只变异种子，不打 API，仍生成报告 |
| `--open` | `-o` | 完成后打开报告 |
| `--config` | `-c` | 配置文件（默认 `config.yaml`） |
| `--inputs` | `-i` | 种子文件（默认 `inputs/samples.yaml`） |

```bash
python src/main.py --demo --open
python src/main.py -c my_config.yaml -i my_inputs.yaml --open
```

---

## 配置

与 `src/config.py` 对齐。旧写法 `agent.url` / `test.mutator_types` 仍能加载。

```yaml
api:
  url: "https://your-agent-api.com/chat"
  method: "POST"
  headers:
    Content-Type: "application/json"
  body_template: |
    {
      "message": "{{message}}"
    }
  response_path: "reply"
  timeout: 30

mutation:
  enabled: "all"          # all / langtest / nlpcda / textattack / giskard
  num_per_type: 5         # 每种变异类型、每条种子最多几条
  demo: false             # true 等同 --demo

giskard:
  description: "请改成当前智能体：它能做什么、必须拒绝什么。"
  languages: ["zh"]
  kind: "vulnerability"   # vulnerability | quality
  max_scenarios: 8

report:
  output_file: "./reports/report.html"
  title: "Agent 变异测试报告"

llm_judge:                # 只给 Giskard 生成攻击/打分，不是被测模型
  enabled: false
```

`--demo` 时 `api.url` 可以空。`enabled: all` 四个库都开；中英用户都在时不要关 TextAttack。

### 种子：每条都会变异

```yaml
# inputs/samples.yaml
# 下面每一行都是一条种子，会各自生成一批变问法
samples:
  - "帮我给张三排李老师的课，明天下午 3 点"
  - "把张三的课改到后天上午"
  - "取消张三明天的课"
  - "查询张三的预约记录"
  - "帮我约王老师的数学课"
  - "Book a math class with teacher Wang tomorrow afternoon"
```

- 中文主要走 **nlpcda**，英文走 **TextAttack**，两种语言都走 **LangTest**。
- `num_per_type: 5` 表示「一条种子 × 一种类型」最多 5 条，不是全局一共 5 条。
- 换智能体 B：只改这个文件和 `api.url`（Giskard 再改 `description`）。

---

## 四个库

| 库 | 干什么 | 输入 | 对「每条种子」做什么 |
| :--- | :--- | :--- | :--- |
| **nlpcda** | 中文变问法 | `samples.yaml` | 近义词、同音、删字、邻字对调、数字写法 |
| **TextAttack** | 英文变问法 | `samples.yaml` | 同义词 / EDA / CheckList |
| **LangTest** | 符号、大小写、空格 | `samples.yaml` | `transform`；没装则回退字符扰动 |
| **Giskard** | 扫 Agent | `giskard.description` + API | **不改种子**，自己出场景打 Agent |

类型对照和约课真实日志（「明天」→「明日午后」等）见 [docs/libraries.md](docs/libraries.md)。

未安装 langtest / textattack 时会跳过或回退，不影响 nlpcda。Giskard 需另装：`pip install "giskard[scan,openai]"`。

---

## 演示 vs 正式

| | `--demo` | 正式 `python src/main.py` |
| :--- | :--- | :--- |
| 变异种子 | 会 | 会 |
| 打 Agent API | 不会 | 会 |
| Giskard | 跳过 | 按 description 扫描 |
| 报告 | 有，状态「未请求」，回复可空 | 有 HTTP 状态和回复 |

---

## 报告里看什么

- **原始输入**：哪条种子。
- **变异输入**：这条种子被改成的句子。
- **变异器 / 类型**：nlpcda 的 `similar_word`、LangTest 的 `spacing` 等。
- 演示模式多一列统计「未请求」，空状态不算失败。

---

## 设计要点

| 点 | 说明 |
| :--- | :--- |
| 每条种子独立变异 | yaml 有 N 条就变 N 组，不是只处理第一条 |
| 请求配置化 | URL / Headers / 响应路径在 `config.yaml` |
| 业务无关 | 约课、查数、查订单都只换种子 |
| 中英都开 | 默认 nlpcda + TextAttack；Giskard 扫 Agent |
| 先看返回再断言 | 现在收 HTTP 和回复；后续加 `code=0` |

---

## 依赖

见 `requirements.txt`：必选 `requests` / `pyyaml` / `jinja2`；变种子 `nlpcda`、`langtest`、`textattack`；扫 Agent 另装 `giskard[scan,openai]`。
