"""A股价值研投｜V10 研究变化追踪
只比较已保存的研究快照，不重新运行核心研究引擎。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from user_store import recent_research

ACCOUNT_KEY = "vs_account"


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or str(value).strip() in {"", "--", "None", "nan", "NaN"}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_num(value: Optional[float], digits: int = 1, suffix: str = "") -> str:
    return "暂无" if value is None else f"{value:.{digits}f}{suffix}"


def _delta(current: Any, previous: Any) -> Optional[float]:
    a, b = _num(current), _num(previous)
    return None if a is None or b is None else a - b


def _direction(score_delta: Optional[float], margin_delta: Optional[float]) -> str:
    signals = []
    if score_delta is not None:
        if score_delta >= 3:
            signals.append(1)
        elif score_delta <= -3:
            signals.append(-1)
    if margin_delta is not None:
        if margin_delta >= 3:
            signals.append(1)
        elif margin_delta <= -3:
            signals.append(-1)
    if not signals:
        return "⚪ 基本稳定"
    total = sum(signals)
    if total > 0:
        return "🟢 研究结论改善"
    if total < 0:
        return "🔴 研究结论走弱"
    return "🟡 出现分化"


def _find_previous(rows: list[Dict[str, Any]], code: str) -> Optional[Dict[str, Any]]:
    found_latest = False
    for row in rows:
        if str(row.get("code") or "") != code:
            continue
        if not found_latest:
            found_latest = True
            continue
        return row
    return None


def render_research_change(code: str, current_snapshot: Optional[Dict[str, Any]] = None) -> None:
    """展示当前股票与上一次同股票研究结果的变化。"""
    account = st.session_state.get(ACCOUNT_KEY)
    if not isinstance(account, dict):
        return

    code = str(code or "").strip()
    if len(code) != 6:
        return

    rows = recent_research(account.get("user_id", ""), limit=30)
    current = dict(current_snapshot or {})
    if not current:
        for row in rows:
            if str(row.get("code") or "") == code:
                current = dict(row)
                break
    if not current:
        return

    previous = _find_previous(rows, code)
    st.markdown("### 🔄 本次研究变化")
    if not previous:
        st.info("🆕 这是该股票第一次保存研究结果。下一次重新研究后，这里会自动显示评分、估值与安全边际变化。")
        return

    score_delta = _delta(current.get("score"), previous.get("score"))
    margin_delta = _delta(current.get("safety_margin"), previous.get("safety_margin"))
    value_delta = _delta(current.get("normal_value"), previous.get("normal_value"))
    price_delta = _delta(current.get("price"), previous.get("price"))

    st.markdown(f"**{_direction(score_delta, margin_delta)}**")
    a, b = st.columns(2)
    a.metric("综合评分变化", _fmt_num(score_delta, 0, "分"), delta=None)
    b.metric("安全边际变化", _fmt_num(margin_delta, 1, "%"), delta=None)
    c, d = st.columns(2)
    c.metric("中性合理价变化", _fmt_num(value_delta, 2, "元"), delta=None)
    d.metric("当前价格变化", _fmt_num(price_delta, 2, "元"), delta=None)

    prev_decision = previous.get("decision") or "暂无"
    curr_decision = current.get("decision") or "暂无"
    if prev_decision != curr_decision:
        st.success(f"🎯 决策变化：**{prev_decision} → {curr_decision}**")
    else:
        st.caption(f"当前决策：{curr_decision}｜上次研究：{str(previous.get('created_at', ''))[:19].replace('T', ' ')}")

    st.caption("以上仅比较已保存研究结果，不重新运行核心研究，不改变原有评分与估值模型。")
