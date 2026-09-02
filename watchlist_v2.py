"""A股价值研投｜我的股票池 V2

商业层模块，不修改核心研究引擎。
V2：展示已完成研究的最新快照，并提供轻量价格提醒与研究报告下载。
当前仍使用 Streamlit session state；正式商业版应迁移到服务端数据库。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

import streamlit as st

from valuation_alert import evaluate_alert, remove_alert, set_alert
from research_report import build_research_report

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


def _to_float(text: Any) -> Any:
    try:
        value = str(text or "").strip()
        return float(value) if value else None
    except (TypeError, ValueError):
        return None


def _render_alert_editor(code: str, snapshot: Dict[str, Any]) -> None:
    """轻量配置：只保存用户主动设置的两个价格。"""
    st.markdown(f"**🔔 {snapshot.get('name', code)} 提醒设置**")
    current = st.session_state.get("vs_valuation_alerts", {}).get(code, {})
    entry_default = current.get("entry_price")
    heavy_default = current.get("heavy_price")

    a, b = st.columns(2)
    with a:
        entry = st.text_input(
            "建仓提醒价",
            value="" if entry_default is None else str(entry_default),
            key=f"vs_alert_entry_{code}",
            placeholder="例如：80",
        )
    with b:
        heavy = st.text_input(
            "重仓提醒价",
            value="" if heavy_default is None else str(heavy_default),
            key=f"vs_alert_heavy_{code}",
            placeholder="例如：70",
        )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("保存", key=f"vs_alert_save_{code}", use_container_width=True):
            set_alert(code, _to_float(entry), _to_float(heavy))
            st.success("✅ 已保存")
            st.rerun()
    with c2:
        if st.button("删除", key=f"vs_alert_delete_{code}", use_container_width=True):
            remove_alert(code)
            st.success("✅ 已删除")
            st.rerun()

    st.caption(f"当前状态：{evaluate_alert(code, snapshot.get('price'))}")


def render_research_report_panel(code: str, snapshot: Dict[str, Any]) -> None:
    """为已完成研究的股票提供 Markdown 报告下载。"""
    if not snapshot:
        st.info("ℹ️ 该股票尚未完成研究，暂无可生成的报告。")
        return
    name = snapshot.get("name", code)
    report = build_research_report(snapshot)
    filename = f"A股价值研投_{code}_{str(name).replace('/', '_')}_研究报告.md"
    st.download_button(
        "📄 下载价值研究报告",
        data=report.encode("utf-8"),
        file_name=filename,
        mime="text/markdown",
        use_container_width=True,
        key=f"vs_report_download_{code}",
    )
    st.caption("报告基于最近一次成功研究快照生成；适合保存、分享与后续人工复核。")


def render_watchlist_dashboard() -> None:
    st.markdown("---")
    st.subheader("⭐ 我的股票池 · 研究跟踪")
    st.caption("展示已经完成研究的最新快照；提醒只做价格状态判断，报告用于研究整理，不发送外部消息。")

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
                    "提醒": evaluate_alert(code, s.get("price")),
                    "跟踪状态": _status(s) if s else "⚪ 尚未研究",
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

        with st.expander("🔔 设置价格提醒", expanded=False):
            target = st.selectbox(
                "选择股票",
                items,
                format_func=lambda x: f"{snapshots.get(x, {}).get('name', x)} ({x})",
                key="vs_alert_target",
            )
            _render_alert_editor(target, snapshots.get(target, {}))

        with st.expander("📄 生成研究报告", expanded=False):
            report_target = st.selectbox(
                "选择已完成研究的股票",
                items,
                format_func=lambda x: f"{snapshots.get(x, {}).get('name', x)} ({x})",
                key="vs_report_target",
            )
            render_research_report_panel(report_target, snapshots.get(report_target, {}))

        c1, c2 = st.columns(2)
        with c1:
            if st.button("清空股票池", key="vs_wl_v2_clear", use_container_width=True):
                clear_watchlist()
                st.rerun()
        with c2:
            st.caption("💡 完成研究后，最新结果会自动更新该股票的快照。")
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
