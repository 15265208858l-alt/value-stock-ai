"""A股价值研投｜我的股票池 V4

商业层模块，不修改核心研究引擎。
V4：股票池从 Streamlit 会话升级为账号绑定的 SQLite 持久化；研究快照仍保留会话展示，完整研究历史由 user_store 管理。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

import streamlit as st

from valuation_alert import evaluate_alert, remove_alert, set_alert
from research_report import build_research_report
from commercial_guard import is_pro
from user_store import (
    add_watchlist_stock,
    clear_watchlist as clear_db_watchlist,
    get_watchlist as get_db_watchlist,
    remove_watchlist_stock,
)

WATCHLIST_KEY = "vs_watchlist"
SNAPSHOT_KEY = "vs_research_snapshots"
MAX_STOCKS = 20
ACCOUNT_KEY = "vs_account"


def _clean_code(value: Any) -> str:
    code = re.sub(r"\D", "", str(value or ""))
    return code if len(code) == 6 else ""


def _user_id() -> str:
    account = st.session_state.get(ACCOUNT_KEY)
    if isinstance(account, dict):
        return str(account.get("user_id", ""))
    return ""


def get_watchlist() -> List[str]:
    """优先读取当前登录账号的持久化股票池；未登录时兼容旧会话数据。"""
    user_id = _user_id()
    if user_id:
        items = get_db_watchlist(user_id, MAX_STOCKS)
        st.session_state[WATCHLIST_KEY] = items
        return items
    items = st.session_state.get(WATCHLIST_KEY, [])
    if not isinstance(items, list):
        return []
    return [x for x in (str(v) for v in items) if re.fullmatch(r"\d{6}", x)]


def add_stock(code: str) -> bool:
    """加入股票池；正式商业功能仅对 Pro 开放。"""
    if not is_pro():
        return False
    code = _clean_code(code)
    if not code:
        return False
    user_id = _user_id()
    if not user_id:
        return False
    ok = add_watchlist_stock(user_id, code, MAX_STOCKS)
    if ok:
        st.session_state[WATCHLIST_KEY] = get_db_watchlist(user_id, MAX_STOCKS)
    return ok


def remove_stock(code: str) -> None:
    if not is_pro():
        return
    code = _clean_code(code)
    user_id = _user_id()
    if user_id:
        remove_watchlist_stock(user_id, code)
        st.session_state[WATCHLIST_KEY] = get_db_watchlist(user_id, MAX_STOCKS)
    else:
        st.session_state[WATCHLIST_KEY] = [x for x in get_watchlist() if x != code]


def clear_watchlist() -> None:
    if not is_pro():
        return
    user_id = _user_id()
    if user_id:
        clear_db_watchlist(user_id)
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
    """记录一次已成功完成核心研究的最新结果。"""
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
    if not is_pro():
        st.warning("🔒 价格提醒为专业会员功能。升级后可为重点股票设置建仓价与重仓价提醒。")
        return

    st.markdown(f"**🔔 {snapshot.get('name', code)} 提醒设置**")
    current = st.session_state.get("vs_valuation_alerts", {}).get(code, {})
    entry_default = current.get("entry_price")
    heavy_default = current.get("heavy_price")
    a, b = st.columns(2)
    with a:
        entry = st.text_input("建仓提醒价", value="" if entry_default is None else str(entry_default), key=f"vs_alert_entry_{code}", placeholder="例如：80")
    with b:
        heavy = st.text_input("重仓提醒价", value="" if heavy_default is None else str(heavy_default), key=f"vs_alert_heavy_{code}", placeholder="例如：70")
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
    if not snapshot:
        st.info("ℹ️ 该股票尚未完成研究，暂无可生成的报告。")
        return
    if not is_pro():
        st.warning("🔒 专业研究报告为 Pro 功能。当前免费版可体验核心研究，升级后解锁报告导出。")
        return
    name = snapshot.get("name", code)
    report = build_research_report(snapshot)
    filename = f"A股价值研投_{code}_{str(name).replace('/', '_')}_研究报告.md"
    st.download_button("📄 下载价值研究报告", data=report.encode("utf-8"), file_name=filename, mime="text/markdown", use_container_width=True, key=f"vs_report_download_{code}")
    st.caption("报告基于最近一次成功研究快照生成；适合保存、分享与后续人工复核。")


def render_watchlist_dashboard() -> None:
    st.markdown("---")
    st.subheader("⭐ 我的股票池 · 研究跟踪")

    if not is_pro():
        st.info("🔒 **我的股票池为专业会员功能**。免费版可以完整研究 1 只股票；升级后可建立最多 20 只重点股票池，并使用价格提醒与专业研究报告。")
        st.caption("商业原则：免费版负责体验核心研究价值，Pro 负责持续跟踪与效率提升。")
        return

    if not _user_id():
        st.warning("👤 请先登录账号，再使用我的股票池。登录后股票池会自动保存，下次登录仍可继续使用。")
        return

    st.caption("股票池已绑定当前账号；展示最近研究快照。价格提醒只做状态判断，不发送外部消息。")
    items = get_watchlist()
    snapshots = _snapshots()

    if items:
        rows: List[Dict[str, Any]] = []
        for code in items:
            s = snapshots.get(code, {})
            rows.append({
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
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        with st.expander("🔔 设置价格提醒", expanded=False):
            target = st.selectbox("选择股票", items, format_func=lambda x: f"{snapshots.get(x, {}).get('name', x)} ({x})", key="vs_alert_target")
            _render_alert_editor(target, snapshots.get(target, {}))

        with st.expander("📄 生成研究报告", expanded=False):
            report_target = st.selectbox("选择已完成研究的股票", items, format_func=lambda x: f"{snapshots.get(x, {}).get('name', x)} ({x})", key="vs_report_target")
            render_research_report_panel(report_target, snapshots.get(report_target, {}))

        c1, c2 = st.columns(2)
        with c1:
            if st.button("清空股票池", key="vs_wl_v4_clear", use_container_width=True):
                clear_watchlist()
                st.rerun()
        with c2:
            st.caption("💡 完成研究后，最新结果会自动更新该股票的快照。")
    else:
        st.info("📌 股票池还是空的。先添加你长期关注的公司，再逐只完成价值研究。")

    with st.expander("＋ 添加股票", expanded=False):
        code_input = st.text_input("股票代码", placeholder="例如：000333", key="vs_wl_v4_add_code")
        a, b = st.columns(2)
        with a:
            if st.button("加入股票池", key="vs_wl_v4_add", use_container_width=True):
                if add_stock(code_input):
                    st.success("✅ 已加入股票池并保存到账号")
                    st.rerun()
                else:
                    st.warning(f"请输入有效6位A股代码，且股票池最多保存{MAX_STOCKS}只。")
        with b:
            code_remove = st.text_input("移除代码", placeholder="例如：000333", key="vs_wl_v4_remove_code")
            if st.button("移除", key="vs_wl_v4_remove", use_container_width=True):
                if code_remove in get_watchlist():
                    remove_stock(code_remove)
                    st.success("✅ 已移除并同步账号数据")
                    st.rerun()
                else:
                    st.info("该股票不在当前股票池。")

    st.caption("🔐 V4：股票池已进入账号 + SQLite 数据层；正式生产环境仍需迁移托管数据库并接入服务端认证。")
