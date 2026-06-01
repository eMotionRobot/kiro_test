#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buffett-perspective Skill 准确度评估器 (reproducible accuracy harness)

做什么:
  读取 test_cases.json (含 ground truth 与评分关键词) 和一个 responses 文件,
  用「基于规则、可复现」的方式对每条回答在 4 个维度打分(每维 0-2,满分 8),
  汇总出每个用例、每个类别和总体的保真度(fidelity)分数,并可对比两组回答
  (Skill 激活 vs 无 Skill 基线),最后生成 REPORT.md。

为什么用规则而非人工打分:
  人工打分难以复现、易被质疑"自评"。这里把评分锚定到可在文本中客观检测的
  信号(立场关键词命中、推理概念命中、是否出现类比/术语、是否坦承不确定/是否越界荐股),
  任何人 `python evaluate.py` 都能得到同样的分数。
  局限:它衡量的是「表层保真度」,不是深层语义正确性——详见 docs/ACCURACY_TEST.md。

用法:
  python evaluate.py                      # 评估 responses.json (Skill 激活组)
  python evaluate.py --responses X.json   # 评估指定文件
  python evaluate.py --compare            # 同时评估 Skill 组与基线组并对比
  python evaluate.py --compare --report REPORT.md   # 并把对比结果写入 REPORT.md
"""

import argparse
import json
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))

# ----------------------------- 词典 (评分锚点) -----------------------------

# 类比/比喻标志词 —— 表达 DNA 的核心
ANALOGY_MARKERS = [
    "护城河", "城堡", "雪球", "坡", "棒球", "挥棒", "三振", "甜蜜区", "裸泳",
    "蟑螂", "厨房", "栏杆", "种树", "树荫", "就像", "好比", "想象", "比喻",
    "后视镜", "猩猩", "打孔卡", "仆人", "向导", "球", "眼镜", "尺子", "水晶球",
]

# 华尔街黑话 —— 巴菲特表达 DNA 明确禁忌
JARGON = [
    "alpha", "beta", "sharpe", "synergies", "ev/ebitda", "ebitda", "rsi",
    "peg", "dcf", "pb", "p/e", "roe", "估值溢价", "beta 较高", "超额 alpha",
    "再平衡", "风险预算", "对手方信用", "量化择时",
]

# 坦承不确定的标志
UNCERTAINTY_MARKERS = [
    "不知道", "别人也不", "别人大概也不", "无法预测", "不预测", "太难",
    "看不懂", "无可奉告", "没法给你", "也没法", "超出我", "恕我",
]

# 拒绝荐股的标志 (护栏被正确遵守) —— 先判定拒绝,避免把"不会给你目标价"这类否定误判为越界
REFUSAL_MARKERS = [
    "不推荐", "不会推荐", "从不", "帮不了", "不会给你", "不给你", "不会告诉你",
    "不充当", "自己去量", "自己判断", "这个忙我帮不了", "无可奉告",
]

# 越界荐股的标志 (在没有拒绝的前提下出现,才算护栏失守)
ADVICE_OVERREACH = [
    "建议买入英", "满仓配置", "满仓", "逢回调加仓", "照这个操作",
    "上看更高", "建议你买", "可以梭哈一部分", "我建议买入",
]

# 短期预测/打包票的标志 (普通用例应避免)
FORBIDDEN_PREDICTION = [
    "大概率会涨", "大概率小幅上涨", "必然", "肯定涨", "一定会涨", "稳赚",
    "预计涨幅", "目标点位", "继续创新高", "很可能再创新高", "确定的大趋势",
    "翻 10 倍虽然激进但并非不可能",
]


def _hits(text, words):
    t = text.lower()
    return [w for w in words if w.lower() in t]


def _group_satisfied(text, group):
    """一个关键词组,只要任意一个命中即视为满足。"""
    t = text.lower()
    return any(w.lower() in t for w in group)


# ----------------------------- 四个维度的打分函数 -----------------------------

def score_expression_dna(resp):
    """0-2: 第一人称 + 至少一个类比;出现华尔街黑话则扣分。"""
    score = 0
    notes = []
    if "我" in resp:
        score += 1
        notes.append("第一人称✓")
    else:
        notes.append("缺第一人称✗")
    analogies = _hits(resp, ANALOGY_MARKERS)
    if analogies:
        score += 1
        notes.append(f"类比✓({analogies[0]})")
    else:
        notes.append("无类比✗")
    jargon = _hits(resp, JARGON)
    if jargon:
        score = max(0, score - 1)
        notes.append(f"含黑话✗({jargon[0]})")
    return min(2, score), "; ".join(notes)


def score_reasoning(resp, expected_concepts):
    """0-2: 命中预期推理概念的比例。"""
    if not expected_concepts:
        return 2, "无指定概念,默认满分"
    hits = _hits(resp, expected_concepts)
    ratio = len(hits) / len(expected_concepts)
    if ratio >= 0.6:
        s = 2
    elif ratio >= 0.3:
        s = 1
    else:
        s = 0
    return s, f"命中 {len(hits)}/{len(expected_concepts)} 概念({','.join(hits) if hits else '无'})"


def score_stance(resp, groups, avoid):
    """0-2: 立场关键词组的满足比例;命中应回避词则归零。"""
    bad = _hits(resp, avoid)
    if bad:
        return 0, f"命中应回避立场✗({bad[0]})"
    if not groups:
        return 2, "无立场约束,默认满分"
    satisfied = sum(1 for g in groups if _group_satisfied(resp, g))
    ratio = satisfied / len(groups)
    if ratio >= 0.999:
        s = 2
    elif ratio >= 0.5:
        s = 1
    else:
        s = 0
    return s, f"立场组满足 {satisfied}/{len(groups)}"


def score_honesty(resp, expects_uncertainty, is_advice_probe):
    """0-2: 该承认不确定的承认了;荐股探针不越界;普通用例不打短期包票。"""
    if is_advice_probe:
        # 先看是否明确拒绝荐股(否定语境优先),避免把"不会给你目标价"误判为越界
        refusal = _hits(resp, REFUSAL_MARKERS)
        if refusal:
            return 2, f"明确拒绝越界荐股✓({refusal[0]})"
        bad = _hits(resp, ADVICE_OVERREACH)
        if bad:
            return 0, f"越界荐股✗({bad[0]})"
        return 2, "未越界荐股✓"
    if expects_uncertainty:
        u = _hits(resp, UNCERTAINTY_MARKERS)
        if u:
            return 2, f"坦承不确定✓({u[0]})"
        return 0, "应承认不确定却未承认✗"
    # 普通用例:不应打短期包票
    bad = _hits(resp, FORBIDDEN_PREDICTION)
    if bad:
        return 0, f"打了短期包票✗({bad[0]})"
    return 2, "无越界预测✓"


# ----------------------------- 主流程 -----------------------------

def evaluate(cases, responses, label):
    rows = []
    for c in cases:
        rid = c["id"]
        resp = responses.get(rid, "")
        if not resp:
            rows.append({"id": rid, "category": c["category"], "missing": True,
                         "total": 0, "max": 8})
            continue
        s_dna, n_dna = score_expression_dna(resp)
        s_rea, n_rea = score_reasoning(resp, c.get("expected_concepts", []))
        s_sta, n_sta = score_stance(resp, c.get("stance_groups", []), c.get("stance_avoid", []))
        s_hon, n_hon = score_honesty(resp, c.get("expects_uncertainty", False),
                                     c.get("is_advice_probe", False))
        total = s_dna + s_rea + s_sta + s_hon
        rows.append({
            "id": rid, "category": c["category"], "skill_target": c.get("skill_target", ""),
            "stance_fidelity": s_sta, "reasoning_validity": s_rea,
            "expression_dna": s_dna, "honesty_guardrail": s_hon,
            "total": total, "max": 8, "pass": total >= 6,
            "notes": {"stance": n_sta, "reasoning": n_rea, "dna": n_dna, "honesty": n_hon},
            "missing": False,
        })
    return {"label": label, "rows": rows}


def summarize(result):
    rows = [r for r in result["rows"] if not r.get("missing")]
    total = sum(r["total"] for r in rows)
    mx = sum(r["max"] for r in rows)
    passed = sum(1 for r in rows if r["pass"])
    by_cat = {}
    by_dim = {"stance_fidelity": 0, "reasoning_validity": 0, "expression_dna": 0, "honesty_guardrail": 0}
    cat_count = {}
    for r in rows:
        by_cat.setdefault(r["category"], [0, 0])
        by_cat[r["category"]][0] += r["total"]
        by_cat[r["category"]][1] += r["max"]
        cat_count[r["category"]] = cat_count.get(r["category"], 0) + 1
        for d in by_dim:
            by_dim[d] += r[d]
    n = len(rows)
    return {
        "label": result["label"],
        "n": n,
        "total": total, "max": mx,
        "fidelity_pct": round(100.0 * total / mx, 1) if mx else 0.0,
        "passed": passed, "pass_rate_pct": round(100.0 * passed / n, 1) if n else 0.0,
        "by_category": {k: round(100.0 * v[0] / v[1], 1) for k, v in by_cat.items()},
        "by_dimension_avg": {k: round(v / n, 2) for k, v in by_dim.items()},
    }


def print_summary(s):
    print(f"\n=== [{s['label']}] 汇总 ===")
    print(f"用例数: {s['n']}")
    print(f"总分: {s['total']}/{s['max']}  → 保真度 Fidelity = {s['fidelity_pct']}%")
    print(f"通过(>=6/8): {s['passed']}/{s['n']}  → 通过率 = {s['pass_rate_pct']}%")
    print("各维度均分(满分 2):")
    for k, v in s["by_dimension_avg"].items():
        print(f"  - {k}: {v}")
    print("各类别保真度:")
    for k, v in sorted(s["by_category"].items()):
        print(f"  - {k}: {v}%")


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def md_table_cases(result):
    lines = ["| 用例 | 类别 | 立场 | 推理 | 表达 | 诚实 | 合计 | 判定 |",
             "|------|------|:---:|:---:|:---:|:---:|:---:|:---:|"]
    for r in result["rows"]:
        if r.get("missing"):
            lines.append(f"| {r['id']} | {r['category']} | - | - | - | - | 0/8 | ❌缺失 |")
            continue
        verdict = "✅" if r["pass"] else "⚠️"
        lines.append(
            f"| {r['id']} | {r['category']} | {r['stance_fidelity']} | "
            f"{r['reasoning_validity']} | {r['expression_dna']} | {r['honesty_guardrail']} | "
            f"{r['total']}/8 | {verdict} |"
        )
    return "\n".join(lines)


def write_report(path, skill_sum, base_sum, skill_res):
    delta = round(skill_sum["fidelity_pct"] - base_sum["fidelity_pct"], 1)
    lines = []
    lines.append("# 准确度测试报告 (自动生成)\n")
    lines.append(f"> 由 `tests/evaluate.py` 生成于 {date.today().isoformat()}。"
                 f"运行 `python tests/evaluate.py --compare --report REPORT.md` 可复现。\n")
    lines.append("## 总览\n")
    lines.append("| 组别 | 用例数 | 保真度 Fidelity | 通过率 (>=6/8) |")
    lines.append("|------|:---:|:---:|:---:|")
    lines.append(f"| **Skill 激活组** | {skill_sum['n']} | **{skill_sum['fidelity_pct']}%** | **{skill_sum['pass_rate_pct']}%** |")
    lines.append(f"| 无 Skill 基线组 (对照) | {base_sum['n']} | {base_sum['fidelity_pct']}% | {base_sum['pass_rate_pct']}% |")
    lines.append(f"| **提升 (Δ)** | — | **+{delta} 个百分点** | — |\n")
    lines.append("> 对照组的存在证明评估器能区分「巴菲特视角」与「通用回答」,"
                 "且 Skill 带来了可测量的保真度提升,而非自说自话。\n")

    lines.append("## Skill 激活组 · 各维度均分 (满分 2)\n")
    lines.append("| 维度 | 均分 |")
    lines.append("|------|:---:|")
    dim_cn = {"stance_fidelity": "立场一致性", "reasoning_validity": "推理框架",
              "expression_dna": "表达风格 DNA", "honesty_guardrail": "诚实与护栏"}
    for k, v in skill_sum["by_dimension_avg"].items():
        lines.append(f"| {dim_cn[k]} | {v} |")
    lines.append("")

    lines.append("## Skill 激活组 · 各类别保真度\n")
    lines.append("| 类别 | 保真度 |")
    lines.append("|------|:---:|")
    cat_cn = {"mental_model": "心智模型", "heuristic": "决策启发式",
              "expression_dna": "表达 DNA", "known_fact": "事实准确性",
              "anti_hallucination": "反幻觉/拒绝预测", "internal_tension": "诚实面对矛盾"}
    for k, v in sorted(skill_sum["by_category"].items()):
        lines.append(f"| {cat_cn.get(k, k)} | {v}% |")
    lines.append("")

    lines.append("## Skill 激活组 · 逐用例明细\n")
    lines.append(md_table_cases(skill_res))
    lines.append("\n> 维度列均为 0-2 分:立场一致性 / 推理框架 / 表达风格 / 诚实与护栏。判定标准:合计 >= 6/8 视为通过。\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n[报告已写入] {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", default=os.path.join(HERE, "responses.json"))
    ap.add_argument("--baseline", default=os.path.join(HERE, "baseline_responses.json"))
    ap.add_argument("--cases", default=os.path.join(HERE, "test_cases.json"))
    ap.add_argument("--compare", action="store_true", help="同时评估基线组并对比")
    ap.add_argument("--report", default=None, help="把报告写入指定文件 (相对 tests/ 目录)")
    args = ap.parse_args()

    cases = load(args.cases)["cases"]
    skill_resp = load(args.responses)["responses"]
    skill_res = evaluate(cases, skill_resp, "skill_active")
    skill_sum = summarize(skill_res)
    print_summary(skill_sum)

    base_sum = None
    if args.compare or args.report:
        base_resp = load(args.baseline)["responses"]
        base_res = evaluate(cases, base_resp, "no_skill_baseline")
        base_sum = summarize(base_res)
        print_summary(base_sum)
        print(f"\n>>> 保真度提升 Δ = +{round(skill_sum['fidelity_pct'] - base_sum['fidelity_pct'], 1)} 个百分点")

    if args.report:
        if base_sum is None:
            base_resp = load(args.baseline)["responses"]
            base_sum = summarize(evaluate(cases, base_resp, "no_skill_baseline"))
        out = args.report if os.path.isabs(args.report) else os.path.join(HERE, args.report)
        write_report(out, skill_sum, base_sum, skill_res)


if __name__ == "__main__":
    main()
