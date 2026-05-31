# Buffett Perspective · 巴菲特思维操作系统（Skill）

> 把沃伦·巴菲特 70 年沉淀的**思考方式**装进你的 AI 助手——让它在你做投资、商业、职业决策时，用巴菲特的视角帮你审视一遍。
>
> A Claude Code / Kiro **Skill** that distills Warren Buffett's cognitive framework into a usable AI perspective.

---

## 这是什么

这是一个 **AI 技能包（Skill）**：当你在对话里说出触发词，AI 会切换成**巴菲特第一人称视角**回答你——大量类比、大白话、坦然认错、不懂就说不懂。

它给的是**判断框架和该问的问题**，**不是**"买入 XX、目标价 YY"的荐股指令。

> 本项目**参考并改编自** [`will2025btc/buffett-perspective`](https://github.com/will2025btc/buffett-perspective)（MIT License，由 Nuwa Skill 框架生成）。
> 在其基础上，本版本（v1.1.0）做了"检查 + 完善"，新增了 ↓

### 相对原项目的改进（"完善"了什么）

| 新增/增强 | 内容 | 在哪 |
|----------|------|------|
| 🔧 **可复用决策工作流** | 把模型和启发式装配成「能力圈→护城河→管理层→估值→永远测试」5 步流水线 | `SKILL.md` |
| ⚠️ **红旗识别清单** | 7 条让巴菲特立刻警惕的危险信号 | `SKILL.md` |
| ✅ **响应自检协议** | 8 项发言前的自检表 + 不荐股的硬性护栏 | `SKILL.md` |
| 📖 **详细使用指南** | 安装、触发、5 类用法 + 完整对话示例、FAQ | `docs/USAGE.md` |
| 💎 **价值分析** | 价值主张、受益人群、ROI 视角、不吹的边界 | `docs/VALUE.md` |
| 🧪 **准确度测试套件** | 24 用例 + 对照组 + 可复现评分器，量化"像不像巴菲特" | `docs/ACCURACY_TEST.md` + `tests/` |

---

## 30 秒上手

```bash
# 1) 安装到 Claude Code 的 skills 目录
cp -r buffett-perspective ~/.claude/skills/buffett-perspective
#    （或在 Kiro 中把 SKILL.md 放进 .kiro/steering/）

# 2) 在对话里说触发词
#    「用巴菲特的视角看看这家公司」/「巴菲特会怎么看」/「Buffett perspective」

# 3) 想要结构化结论时加一句
#    「请按你的决策工作流一步步分析」

# 4) 退出
#    「退出」/「切回正常」
```

---

## 目录结构

```
buffett-perspective/
├── README.md                 # 本文件：总览 + 快速开始
├── SKILL.md                  # ★ 核心技能定义（被 AI 加载的部分）
├── LICENSE                   # MIT
├── docs/
│   ├── USAGE.md              # 使用指南（怎么用，含对话示例）
│   ├── VALUE.md              # 价值分析（值不值得用）
│   └── ACCURACY_TEST.md      # 准确度测试与验证（怎么证明它像巴菲特）
├── references/research/      # 证据基线：6 份调研（改编自原项目，作测试 ground truth）
│   ├── 01-writings.md        # 著作与系统性长文
│   ├── 02-conversations.md   # 对话、访谈、问答
│   ├── 03-expression-dna.md  # 表达风格分析
│   ├── 04-external-views.md  # 外部视角与批评
│   ├── 05-decisions.md       # 重大决策与失误
│   └── 06-timeline.md        # 人物时间线
└── tests/                    # ★ 准确度测试套件
    ├── test_cases.json       # 24 个用例 + ground truth + 评分关键词
    ├── responses.json        # Skill 激活组的参考回答
    ├── baseline_responses.json  # 无 Skill 对照组（control）
    ├── evaluate.py           # 可复现的规则化评分器
    └── REPORT.md             # 自动生成的测试报告
```

---

## 内含什么（Skill 本体）

- **6 个核心心智模型**：经济护城河、能力圈、市场先生、复利滚雪球、制度性强制力、所有者思维
- **8 条决策启发式**：安全边际、管理层诚信、打孔卡、棒球甜蜜区、蟑螂规则、5 分钟规则、报纸测试、"太难"篮子
- **1 套决策工作流 + 1 张红旗清单 + 1 套响应自检协议**（v1.1 新增）
- **完整表达 DNA**：短句 + 大量类比 + 自嘲幽默 + Plain English + 坦然承认无知
- **诚实边界**：明确列出 Skill 的 6 条局限

---

## 准确度，一眼看懂

| 组别 | 保真度 | 通过率 (≥6/8) |
|------|:---:|:---:|
| **Skill 激活组** | **93.2%** | **100% (24/24)** |
| 无 Skill 对照组 | 24.5% | 0% |

> 同样 24 个问题，加载 Skill 后保真度从 24.5% 跃升到 93.2%（+68.7 个百分点）。
> 方法、用例、复现命令与诚实边界见 [`docs/ACCURACY_TEST.md`](docs/ACCURACY_TEST.md)。复现：`python3 tests/evaluate.py --compare`。

---

## ⚠️ 重要声明

- 本 Skill 用于**思维训练与视角切换**，基于巴菲特公开资料**推断**，**非本人观点**，**不构成任何投资建议**。
- 它**不提供**个性化买卖指令或目标价；股市有风险，决策与风险由你自己承担。
- 巴菲特的部分超额收益来自普通人无法复制的结构性优势（保险浮存金、声誉、信息优势），Skill 给你框架，给不了这些。

---

## 致谢与许可

- 原始 Skill 与调研：[`will2025btc/buffett-perspective`](https://github.com/will2025btc/buffett-perspective)（MIT），由 [Nuwa Skill](https://github.com/alchaincyf/nuwa-skill) 生成。
- 本改编版同样以 **MIT License** 释出，详见 [`LICENSE`](LICENSE)。
- 与本仓库的《散户AI炒股实战指南》互补：那份讲"工作流与纪律"，这个 Skill 补"判断哲学"。
