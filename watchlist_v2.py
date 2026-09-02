"""A股价值研投｜我的股票池 V2

商业层模块，不修改核心研究引擎。
V2 的关键设计：把“已经完成的核心研究结果”保存成轻量快照，
股票池负责展示与跟踪，不在这里重复实现财务/估值算法。
当前仍使用 Streamlit session state；正式商业版应迁移到服务端数据库。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

import streamlit as st

WATCHLIST_KEY = "vs_watchlist"
SNAPSHOT_KEY = "vs_research_snapshots"
MAX_STOCKS = 20


def _clean_code(value: Any) -> str:
    code = re.sub(r"\D", "", str(value or ""))
    return code if len(code) == 6 else ""


def get_watchlist() -> List[str]:
    items = st.session_state.get(WATCHLIST_KEY, [])
    if not isinstance(items, list):
        return []
    return [x for x in (str(v) for v in items) if re.fullmatch(r"\d{6}", x)]


def add_stock(code: str) -> bool:
    code = _clean_code(code)
    if not code:
        return False
    items = get_watchlist()
    if code in items:
        return True
    if len(items) >= MAX_STOCKS:
        return False
    items.append(code)
    st.session_state[WATCHLIST_KEY] = items
    return True


def remove_stock(code: str) -> None:
    code = _clean_code(code)
    st.session_state[WATCHLIST_KEY] = [x for x in get_watchlist() if x != code]


def clear_watchlist() -> None:
    st.session_state[WATCHLIST_KEY] = []


def _snapshots() -> Dict[str, Dict[str, Any]]:
    value = st.session_state.get(SNAPSHOT_KEY, {})
    return value if isinstance(value, dict) else {}


def record_research_snapshot(
    *,
    code: str,
    name: str,
    price: Any,
    score: Any,
    rating: str,
    decision: str,
    action: str,
    position: str,
    normal_value: Any,
    safety_margin: Any,
    valuation_level: str,
    historical_level: str,
    risk_level: str,
) -> None:
    """记录一次已成功完成核心研究的结果。"""
    code = _clean_code(code)
    if not code:
        return
    snapshots = _snapshots()
    snapshots[code] = {
        "code": code,
        "name": str(name or code),
        "price": price,
        "score": score,
        "rating": str(rating or "暂无"),
        "decision": str(decision or "暂无"),
        "action": str(action or "暂无"),
        "position": str(position or "暂无"),
        "normal_value": normal_value,
        "safety_margin": safety_margin,
        "valuation_level": str(valuation_level or "数据不足"),
        "historical_level": str(historical_level or "数据不足"),
        "risk_level": str(risk_level or "数据不足"),
    }
    st.session_state[SNAPSHOT_KEY] = snapshots


def _fmt_num(value: Any, suffix: str = "") -> str:
    try:
        if value is None or value == "":
            return "暂无"
        return f"{float(value):.2f}{suffix}"
    except (TypeError, ValueError):
        return "暂无"


def _status(snapshot: Dict[str, Any]) -> str:
    decision = snapshot.get("decision", "")
    valuation = snapshot.get("valuation_level", "")
    risk = snapshot.get("risk_level", "")
    if "回避" in decision or "高风险" in risk:
        return "🔴 高风险"
    if "建仓" in decision or "试探" in decision:
        return "🟢 可研究"
    if "等待" in decision or "高估" in valuation:
        return "🟡 等待"
    if "继续观察" in decision or "观察" in decision:
        return "🟠 观察"
    return "⚪ 数据不足"


def render_watchlist_dashboard() -> None:
    st.markdown("---")
    st.subheader("⭐ 我的股票池 · 研究跟踪")
    st.caption("只展示已经完成研究的最新快照；不重复执行核心估值计算。正式会员版将升级为云端持续跟踪。")

    items = get_watchlist()
    snapshots = _snapshots()

    if items:
        rows: List[Dict[str, Any]] = []
        for code in items:
            s = snapshots.get(code, {})
            rows.append(
                {
                    "股票": f"{s.get('name', code)} ({code})",
                    "评分": _fmt_num(s.get("score")),
                    "评级": s.get("rating", "未研究"),
                    "当前价": _fmt_num(s.get("price")),
                    "合理价": _fmt_num(s.get("normal_value")),
                    "安全边际": _fmt_num(s.get("safety_margin"), "%"),
                    "估值": s.get("valuation_level", "未研究"),
                    "风险": s.get("risk_level", "未研究"),
                    "跟踪状态": _status(s) if s else "⚪ 尚未研究",
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("清空股票池", key="vs_wl_v2_clear", use_container_width=True):
                clear_watchlist()
                st.rerun()
        with c2:
            st.caption("💡 研究任意股票后回到股票池，最新研究结果会自动更新该股票的快照。")
    else:
        st.info("📌 股票池还是空的。先添加你长期关注的公司，再逐只完成价值研究。")

    with st.expander("＋ 添加股票", expanded=False):
        code_input = st.text_input("股票代码", placeholder="例如：000333", key="vs_wl_v2_add_code")
        a, b = st.columns(2)
        with a:
            if st.button("加入股票池", key="vs_wl_v2_add", use_container_width=True):
                if add_stock(code_input):
                    st.success("✅ 已加入股票池")
                    st.rerun()
                else:
                    st.warning(f"请输入有效6位A股代码，且股票池最多保存{MAX_STOCKS}只。")
        with b:
            code_remove = st.text_input("移除代码", placeholder="例如：000333", key="vs_wl_v2_remove_code")
            if st.button("移除", key="vs_wl_v2_remove", use_container_width=True):
                if code_remove in get_watchlist():
                    remove_stock(code_remove)
                    st.success("✅ 已移除")
                    st.rerun()
                else:
                    st.info("该股票不在当前股票池。")

    st.caption("🔐 当前 V2 为会话原型；正式收费版必须使用服务端账户、数据库与权限校验。")
