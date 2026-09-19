"""A股价值研投｜V21 一键专业研究报告
只消费已完成的研究快照，不修改评分、估值与风险引擎。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List


def _num(value: Any):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value: Any, digits: int = 2, suffix: str = "") -> str:
    value = _num(value)
    if value is None:
        return "暂无"
    return f"{value:.{digits}f}{suffix}"


def _pct(value: Any, digits: int = 1) -> str:
    value = _num(value)
    if value is None:
        return "暂无"
    return f"{value * 100:.{digits}f}%"


def _ratio(value: Any, digits: int = 2) -> str:
    value = _num(value)
    if value is None:
        return "暂无"
    return f"{value:.{digits}f}x"


def _clean_text(value: Any, default: str = "暂无") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _record_rows(rows: Any) -> List[Dict[str, Any]]:
    if rows is None:
        return []
    if hasattr(rows, "to_dict"):
        try:
            return list(rows.to_dict("records"))
        except Exception:
            return []
    if isinstance(rows, list):
        return [x for x in rows if isinstance(x, dict)]
    return []


def _latest_change(rows: List[Dict[str, Any]], column: str):
    values = []
    for row in rows:
        value = _num(row.get(column))
        if value is not None:
            values.append(value)
    if len(values) < 2:
        return None
    return values[-1] - values[0]


def _trend_sentence(rows: List[Dict[str, Any]]) -> str:
    if len(rows) < 2:
        return "历史样本不足，暂不能形成稳定趋势结论。"

    parts = []
    first = rows[0]
    last = rows[-1]

    revenue_first = _num(first.get("营业收入"))
    revenue_last = _num(last.get("营业收入"))
    if revenue_first is not None and revenue_last is not None and revenue_first != 0:
        parts.append(
            f"营业收入由{revenue_first / 1e8:.1f}亿元变为{revenue_last / 1e8:.1f}亿元"
        )

    profit_last = _num(last.get("净利润"))
    if profit_last is not None:
        parts.append(f"最新净利润约{profit_last / 1e8:.1f}亿元")

    ocf_last = _num(last.get("经营现金流"))
    if ocf_last is not None:
        parts.append(f"最新经营现金流约{ocf_last / 1e8:.1f}亿元")

    fcf_last = _num(last.get("自由现金流"))
    if fcf_last is not None:
        parts.append(f"最新自由现金流约{fcf_last / 1e8:.1f}亿元")

    return "；".join(parts) if parts else "历史样本存在，但核心字段不足。"


def _build_risk_list(p: Dict[str, Any]) -> List[str]:
    risks: List[str] = []
    risk = p.get("risk") or {}
    fcf = p.get("fcf") or {}
    governance = p.get("governance") or {}
    vr = p.get("valuation") or {}
    trend = _record_rows(p.get("trend"))

    if risk.get("hard_veto") or fcf.get("hard_veto"):
        risks.append("风险闸门已触发：现金流或核心财务质量存在硬风险，低估值不能覆盖该风险。")
    else:
        for item in risk.get("risk_items") or []:
            if item not in risks:
                risks.append(str(item))

    if fcf.get("level") and fcf.get("level") not in {"良好", "数据不足"}:
        risks.append(f"自由现金流状态：{fcf.get('level')}。")

    debt = _num(p.get("debt"))
    if debt is not None and debt >= 70:
        risks.append(f"资产负债率约{debt:.1f}%，杠杆水平偏高。")

    if governance.get("level") == "需要关注":
        risks.append("公司治理模块存在需要进一步核查的事项。")

    valuation_status = _clean_text(vr.get("valuation_status"), "数据不足")
    if valuation_status in {"高估区", "偏贵区"}:
        risks.append(f"当前估值状态为{valuation_status}，安全边际偏弱。")

    for col, label in [("应收/营收", "应收/营收"), ("存货/营收", "存货/营收"), ("商誉/总资产", "商誉/总资产")]:
        delta = _latest_change(trend, col)
        if delta is not None and delta >= 0.05:
            risks.append(f"{label}较历史样本提高约{delta * 100:.1f}个百分点，需继续观察质量变化。")

    return risks[:8]


def _build_follow_items(p: Dict[str, Any]) -> List[str]:
    score = p.get("score") or {}
    fcf = p.get("fcf") or {}
    trend = _record_rows(p.get("trend"))
    weak = p.get("radar_weak") or []
    items: List[str] = []

    weak_text = {str(x) for x in weak}
    if "现金流质量" in weak_text or fcf.get("ocf_to_profit") is not None:
        items.append("经营现金流/净利润：观察是否持续接近或高于1倍，并同步核查自由现金流。")
    if "成长能力" in weak_text:
        items.append("营收与净利润增速：重点观察增长是否持续，以及利润增速是否明显偏离营收。")
    if "企业质量" in weak_text:
        items.append("ROE与盈利能力：观察ROE是否稳定，以及盈利改善是否伴随现金流改善。")
    if "资产负债" in weak_text:
        items.append("资产负债率：关注杠杆上升是否快于盈利与现金流增长。")
    if "营运资本" in weak_text:
        items.append("应收与存货：重点观察其增速是否长期快于营收，以及回款与周转是否恶化。")
    if "当前估值" in weak_text or "历史估值" in weak_text:
        items.append("估值与安全边际：跟踪当前PE/PB、历史估值分位及中性合理价变化。")
    if "同行竞争" in weak_text:
        items.append("同行比较：跟踪ROE、利润增速、PE/PB等相对位置是否持续。")
    if "盈利兑现" in weak_text:
        items.append("盈利兑现：观察净利润是否能够稳定转化为经营现金流。")

    if "商誉/总资产" in {k for row in trend for k in row.keys()}:
        items.append("商誉与减值：关注商誉/总资产变化，并结合年报附注核查减值迹象。")

    if not items:
        items.extend([
            "营收与净利润增长是否延续。",
            "经营现金流与净利润是否持续匹配。",
            "估值是否回落至更有安全边际的区间。",
            "核心风险项是否出现恶化。",
        ])

    # 去重并限制长度
    out = []
    for item in items:
        if item not in out:
            out.append(item)
    return out[:7]


def _build_step_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "10步分析数据暂无。"

    headers = ["步骤", "判断", "证据", "证据性质"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|---|---|---|---|",
    ]
    for row in rows:
        step = _clean_text(row.get("步骤"))
        judgment = _clean_text(row.get("判断"))
        evidence = _clean_text(row.get("证据")).replace("|", "｜")
        nature = _clean_text(row.get("证据性质"))
        lines.append(f"| {step} | {judgment} | {evidence} | {nature} |")
    return "\n".join(lines)


def build_research_report_v21(payload: Dict[str, Any]) -> str:
    """把当前页面已完成的研究结果整理成专业、可保存、可下载的 Markdown 报告。"""
    p = payload or {}
    code = _clean_text(p.get("code"), "")
    name = _clean_text(p.get("name"), code or "目标公司")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    score = p.get("score") or {}
    vr = p.get("valuation") or {}
    fcf = p.get("fcf") or {}
    governance = p.get("governance") or {}
    radar_weak = p.get("radar_weak") or []
    trend = _record_rows(p.get("trend"))
    steps = _record_rows(p.get("step_table"))

    score_value = _num(score.get("score"))
    price = _num(p.get("price"))
    normal_value = _num(vr.get("normal"))
    safety_margin = _num(vr.get("safety_margin"))
    roe = _num(p.get("roe"))
    debt = _num(p.get("debt"))
    revenue_growth = _num(p.get("revenue_growth"))
    profit_growth = _num(p.get("profit_growth"))
    cash_ratio = _num(p.get("cash_ratio"))
    peer_score = _num(p.get("peer_score"))
    hist_percentile = _num(p.get("historical_percentile"))
    annual_eps = _num(p.get("annual_eps"))
    normalized_eps = _num(p.get("normalized_eps"))

    if safety_margin is None:
        valuation_note = "安全边际暂无，需结合实时价格和估值数据再次确认。"
    elif safety_margin >= 0.2:
        valuation_note = "当前价格低于中性合理价值，模型安全边际相对明显。"
    elif safety_margin >= 0:
        valuation_note = "当前价格接近或略低于中性合理价值，安全边际处于一般水平。"
    else:
        valuation_note = "当前价格高于中性合理价值，模型安全边际偏弱。"

    trend_text = _trend_sentence(trend)
    risks = _build_risk_list(p)
    follow_items = _build_follow_items(p)

    current_profile = [
        f"行业：{_clean_text(p.get('industry'), '数据不足')}",
        f"综合评分：{_fmt(score_value, 0)}/100",
        f"评级：{_clean_text(score.get('rating'))}",
        f"研究可信度：{_clean_text(score.get('data_confidence'))}",
        f"研究状态：{_clean_text(score.get('research_status'))}",
    ]

    financial_items = [
        f"ROE：{_fmt(roe, 1, '%')}",
        f"营收增速：{_fmt(revenue_growth, 1, '%')}",
        f"净利润增速：{_fmt(profit_growth, 1, '%')}",
        f"经营现金流/净利润：{_ratio(cash_ratio)}",
        f"资产负债率：{_fmt(debt, 1, '%')}",
        f"同行竞争力：{_fmt(peer_score, 0)}/100",
    ]

    valuation_items = [
        f"当前价格：{_fmt(price)} 元",
        f"年度EPS：{_fmt(annual_eps)} 元",
        f"正常化EPS：{_fmt(normalized_eps)} 元",
        f"保守价值：{_fmt(vr.get('conservative'))} 元",
        f"中性合理价：{_fmt(normal_value)} 元",
        f"乐观价值：{_fmt(vr.get('optimistic'))} 元",
        f"建仓参考价：{_fmt(vr.get('entry_price'))} 元",
        f"重仓参考价：{_fmt(vr.get('heavy_price'))} 元",
        f"历史PE分位：{_fmt(hist_percentile, 1, '%')}",
        f"安全边际：{_pct(safety_margin)}",
    ]

    fcf_items = [
        f"自由现金流：{_fmt(fcf.get('fcf') / 1e8 if _num(fcf.get('fcf')) is not None else None, 1, '亿元')}",
        f"经营现金流/净利润：{_ratio(fcf.get('ocf_to_profit'))}",
        f"资本开支/经营现金流：{_ratio(fcf.get('capex_to_ocf'))}",
        f"现金流质量：{_clean_text(fcf.get('level'))}",
        f"现金流硬否决：{'是' if fcf.get('hard_veto') else '否'}",
    ]

    governance_items = [
        f"治理数据：{'可分析' if governance.get('available') else '数据不足'}",
        f"治理等级：{_clean_text(governance.get('level'))}",
        f"治理风险分：{_fmt(governance.get('score'), 0)}/4" if governance.get("available") else "治理风险分：—",
    ]

    weak_text = "、".join(str(x) for x in radar_weak) if radar_weak else "暂无"
    decision = _clean_text(p.get("decision"))
    action = _clean_text(p.get("action"))
    position = _clean_text(p.get("position"))
    risk_level = _clean_text(p.get("decision_risk_level"), _clean_text(score.get("risk_level")))

    report = f"""# A股价值研投｜{name}（{code}）V21 一键专业研究报告

**生成时间：** {generated_at}

> 本报告由 ValueStock AI 基于本次研究页面已经取得的结构化数据自动整理。报告将“数据事实、模型判断、研究线索与待核查事项”分开表达；不补写未取得的数据，也不把可能原因当作事实。

## 一、公司画像与研究状态

{"；".join(current_profile)}

### 本次研究核心定位

- 当前决策：**{decision}**
- 建议操作：**{action}**
- 建议仓位：**{position}**
- 风险状态：**{risk_level}**
- 当前模型相对短板：**{weak_text}**

## 二、长期价值投资10步检查表

{_build_step_table(steps)}

> 第2步“护城河”、第8步商誉/减值、第9步公司治理等，不应仅依据单一财务指标作自动化定性；报告中的“数据不足”保留为研究状态，不强行打分。

## 三、5年核心财务质量趋势

{trend_text}

### 当前核心财务指标

{"；".join(financial_items)}

### 趋势观察

"""
    if trend:
        last = trend[-1]
        first = trend[0]
        trend_rows = []
        for col, label, pct_mode in [
            ("应收/营收", "应收/营收", True),
            ("存货/营收", "存货/营收", True),
            ("商誉/总资产", "商誉/总资产", True),
            ("资本开支/经营现金流", "资本开支/经营现金流", False),
        ]:
            delta = _latest_change(trend, col)
            if delta is not None:
                trend_rows.append(
                    f"- {label}样本变动：{delta * 100:+.1f}个百分点" if pct_mode else f"- {label}样本变动：{delta:+.2f}倍"
                )
        report += "\n".join(trend_rows) if trend_rows else "- 当前趋势比率数据不足，暂不作趋势性结论。"
    else:
        report += "- 年度趋势数据不足，暂不作趋势性结论。"

    report += f"""

## 四、现金流与资本开支

{"；".join(fcf_items)}

**研究含义：** 现金流指标用于验证利润质量。若经营现金流明显弱于利润，或自由现金流触发硬风险，报告优先保留风险结论，而不是用估值便宜进行抵消。

## 五、估值与安全边际

### 估值区间

{"；".join(valuation_items)}

**估值判断：** {_clean_text(vr.get('valuation_status'))}

**价格解释：** {valuation_note}

> 估值区间是模型结果，不代表未来价格一定会达到对应水平。估值有效性取决于盈利质量、数据完整度和模型适用性。

## 六、历史估值与同行比较

- 历史估值判断：**{_clean_text(p.get('historical_level'))}**
- 历史PE分位：**{_fmt(hist_percentile, 1, '%')}**
- 同行竞争力：**{_fmt(peer_score, 0)}/100**
- 同行相对估值：**{_clean_text(p.get('relative_valuation_level'))}**
- 数据不足时，不将同行缺失自动解释成竞争力下降。

## 七、公司治理与结构风险

{"；".join(governance_items)}

治理模块当前结论：**{_clean_text(governance.get('level'))}**

## 八、核心风险清单

"""
    if risks:
        report += "\n".join(f"{i}. {item}" for i, item in enumerate(risks, 1))
    else:
        report += "当前结构化风险模块未发现高优先级异常；仍需结合最新年报、公告及业务信息持续核查。"

    report += """

## 九、后续关键跟踪指标

"""
    report += "
".join(f"{i}. {item}" for i, item in enumerate(follow_items, 1))

    report += f"""

## 十、本次研究摘要

**企业质量：** {_clean_text(score.get('risk_level'), '数据不足')}  
**综合评分：** {_fmt(score_value, 0)}/100  
**估值状态：** {_clean_text(score.get('valuation_level'))}  
**历史估值：** {_clean_text(score.get('historical_level'))}  
**风险状态：** {risk_level}  
**安全边际：** {_pct(safety_margin)}  

**当前研究结论：** {decision}｜{action}｜{position}

### 研究方法说明

本报告沿用 ValueStock AI 已有的长期价值投资研究框架：企业质量、成长、现金流、资产负债表、营运资本、估值、历史估值、同行比较、盈利兑现与风险否决。V21 只负责把结果组织为完整研究报告，不重新计算核心评分。

---

**A股价值研投｜ValueStock AI V21**  
*用AI研究价值，而不是追逐情绪。*

**免责声明：** 本报告仅用于证券市场研究辅助与信息整理，不构成任何证券投资建议、收益承诺或买卖依据。实际投资应结合最新公告、财务报告、行业变化、估值变化及个人风险承受能力独立判断。
"""
    return report
