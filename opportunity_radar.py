"""A股价值研投｜投资机会雷达 V1
只读取账号已保存的研究结果，不重新运行核心研究引擎。
"""
from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd
import streamlit as st
from commercial_guard import is_pro
from user_store import recent_research

ACCOUNT_KEY = "vs_account"


def _user_id() -> str:
    account = st.session_state.get(ACCOUNT_KEY)
    return str(account.get("user_id", "")) if isinstance(account, dict) else ""


def _num(value: Any):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _latest(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for row in rows or []:
        code = str(row.get("code") or "").strip()
        if len(code) != 6 or code in seen:
            continue
        seen.add(code)
        out.append(dict(row))
    return out


def _rank(rows: List[Dict[str, Any]], key: str, reverse: bool = True):
    valid = [r for r in rows if _num(r.get(key)) is not None]
    valid.sort(key=lambda r: _num(r.get(key)), reverse=reverse)
    return valid


def render_opportunity_radar() -> None:
    """展示最近研究中的低估、质量和综合机会，不消耗新的研究额度。"""
    uid = _user_id()
    if not uid:
        return

    rows = _latest(recent_research(uid, limit=20))
    if not rows:
        return

    margin_rows = _rank(rows, "safety_margin")
    score_rows = _rank(rows, "score")
    composite = []
    for row in rows:
        margin = _num(row.get("safety_margin"))
        score = _num(row.get("score"))
        if margin is None and score is None:
            continue
        # 安全边际60% + 综合评分40%，仅用于展示排序，不修改核心评分。
        radar_score = (margin if margin is not None else -100.0) * 0.6 + (score if score is not None else 0.0) * 0.4
        item = dict(row)
        item["radar_score"] = radar_score
        composite.append(item)
    composite.sort(key=lambda r: r["radar_score"], reverse=True)

    limit = 5 if is_pro() else 3
    st.markdown("### 🎯 投资机会雷达")
    st.caption("基于你已经完成的研究结果排序；不会重新跑核心研究，也不会额外消耗研究额度。")

    tabs = st.tabs(["🔥 综合优先", "💰 安全边际", "🏆 企业评分"])
    groups = [composite, margin_rows, score_rows]
    for tab, group in zip(tabs, groups):
        with tab:
            if not group:
                st.info("暂无足够数据形成排行。")
                continue
            data = []
            for i, row in enumerate(group[:limit], 1):
                data.append({
                    "排名": f"Top {i}",
                    "股票": f"{row.get('name') or row.get('code')} ({row.get('code')})",
                    "评分": "暂无" if _num(row.get("score")) is None else f"{_num(row.get('score')):.0f}",
                    "安全边际": "暂无" if _num(row.get("safety_margin")) is None else f"{_num(row.get('safety_margin')):.1f}%",
                    "当前价": "暂无" if _num(row.get("price")) is None else f"{_num(row.get('price')):.2f}",
                    "合理价": "暂无" if _num(row.get("normal_value")) is None else f"{_num(row.get('normal_value')):.2f}",
                    "决策": row.get("decision") or "暂无",
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    if not is_pro():
        st.info("⭐ 免费版展示 Top 3；升级 Pro 后可扩展到 Top 5，并结合股票池、行情跟踪、估值提醒和研究报告。")
    else:
        st.success("⭐ Pro：已开放 Top 5 投资机会雷达。")
