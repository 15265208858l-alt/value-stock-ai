"""A股价值研投｜估值变化提醒 V11
只读取账号已保存的研究历史，不重新运行核心研究，不修改核心估值逻辑。
"""
from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from commercial_guard import is_pro
from user_store import recent_research

ACCOUNT_KEY = "vs_account"


def _num(value: Any):
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _latest_two(rows: List[Dict[str, Any]]):
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows or []:
        code = str(row.get("code") or "").strip()
        if not code:
            continue
        grouped.setdefault(code, []).append(row)
    return [(code, items[0], items[1]) for code, items in grouped.items() if len(items) >= 2]


def render_valuation_change_alerts() -> None:
    account = st.session_state.get(ACCOUNT_KEY)
    if not isinstance(account, dict):
        return

    rows = recent_research(account.get("user_id", ""), limit=40)
    alerts = []
    for code, latest, previous in _latest_two(rows):
        latest_value = _num(latest.get("normal_value"))
        previous_value = _num(previous.get("normal_value"))
        latest_margin = _num(latest.get("safety_margin"))
        previous_margin = _num(previous.get("safety_margin"))
        latest_score = _num(latest.get("score"))
        previous_score = _num(previous.get("score"))

        reasons = []
        value_change = None
        if latest_value is not None and previous_value not in (None, 0):
            value_change = (latest_value / previous_value - 1) * 100
            if abs(value_change) >= 5:
                reasons.append(f"合理价值 {value_change:+.1f}%")

        margin_change = None
        if latest_margin is not None and previous_margin is not None:
            margin_change = latest_margin - previous_margin
            if abs(margin_change) >= 5:
                reasons.append(f"安全边际 {margin_change:+.1f}个百分点")

        score_change = None
        if latest_score is not None and previous_score is not None:
            score_change = latest_score - previous_score
            if abs(score_change) >= 5:
                reasons.append(f"评分 {score_change:+.0f}")

        if not reasons:
            continue

        alerts.append({
            "code": code,
            "name": latest.get("name") or code,
            "latest": latest,
            "reasons": reasons,
            "value_change": value_change,
            "margin_change": margin_change,
            "score_change": score_change,
        })

    st.markdown("### 🔔 估值变化提醒")
    st.caption("仅比较你已经保存的两次研究结果；达到明显变化阈值才提醒，不会重新运行研究。")

    if not alerts:
        st.success("✅ 最近研究暂未发现明显的估值、评分或安全边际变化。")
        return

    alerts.sort(
        key=lambda x: max(
            abs(x.get("value_change") or 0),
            abs(x.get("margin_change") or 0),
            abs(x.get("score_change") or 0),
        ),
        reverse=True,
    )
    limit = 5 if is_pro() else 3
    for item in alerts[:limit]:
        latest = item["latest"]
        st.warning(
            f"🔔 **{item['name']} ({item['code']})**｜"
            + "｜".join(item["reasons"])
            + f"｜当前结论：{latest.get('decision') or '暂无'}"
        )
