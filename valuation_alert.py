"""A股价值研投｜轻量估值提醒 V1

只负责本地会话级提醒配置，不修改核心研究引擎，也不发送外部消息。
正式商业版再接入账号、数据库和通知渠道。
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import streamlit as st

ALERTS_KEY = "vs_valuation_alerts"


def _alerts() -> Dict[str, Dict[str, Any]]:
    value = st.session_state.get(ALERTS_KEY, {})
    return value if isinstance(value, dict) else {}


def set_alert(code: str, entry_price: Optional[float], heavy_price: Optional[float]) -> None:
    code = str(code or "").strip()
    if not code:
        return
    alerts = _alerts()
    alerts[code] = {
        "entry_price": entry_price,
        "heavy_price": heavy_price,
    }
    st.session_state[ALERTS_KEY] = alerts


def remove_alert(code: str) -> None:
    alerts = _alerts()
    alerts.pop(str(code or "").strip(), None)
    st.session_state[ALERTS_KEY] = alerts


def evaluate_alert(code: str, price: Any) -> str:
    alert = _alerts().get(str(code or "").strip())
    try:
        p = float(price)
    except (TypeError, ValueError):
        return "⚪ 当前价格暂无"
    if not alert:
        return "⚪ 未设置提醒"
    heavy = alert.get("heavy_price")
    entry = alert.get("entry_price")
    try:
        if heavy is not None and p <= float(heavy):
            return "🔴 已达到重仓参考价"
        if entry is not None and p <= float(entry):
            return "🟢 已达到建仓参考价"
    except (TypeError, ValueError):
        pass
    return "🟡 尚未触发"


def render_alert_panel(code: str, price: Any, entry_price: Any, heavy_price: Any) -> None:
    """研究完成后显示提醒配置；只有用户主动保存才写入 session state。"""
    st.subheader("🔔 估值提醒")
    st.caption("设置两个价格即可：跌至建仓参考价提醒；跌至重仓参考价强提醒。当前仅保存在本次会话。")

    current = _alerts().get(str(code or "").strip(), {})
    saved_entry = current.get("entry_price", entry_price)
    saved_heavy = current.get("heavy_price", heavy_price)

    c1, c2 = st.columns(2)
    with c1:
        entry_text = st.text_input("建仓提醒价（元）", value="" if saved_entry is None else str(saved_entry), key=f"alert_entry_{code}")
    with c2:
        heavy_text = st.text_input("重仓提醒价（元）", value="" if saved_heavy is None else str(saved_heavy), key=f"alert_heavy_{code}")

    a, b = st.columns(2)
    with a:
        if st.button("保存提醒", key=f"alert_save_{code}", use_container_width=True):
            def num(text):
                try:
                    return float(text) if str(text).strip() else None
                except (TypeError, ValueError):
                    return None
            set_alert(code, num(entry_text), num(heavy_text))
            st.success("✅ 提醒已保存")
            st.rerun()
    with b:
        if st.button("删除提醒", key=f"alert_remove_{code}", use_container_width=True):
            remove_alert(code)
            st.success("✅ 提醒已删除")
            st.rerun()

    st.info(evaluate_alert(code, price))
    st.caption("🔐 V1 不发送短信、微信或邮件，也不保存支付等敏感信息；正式版再接入服务端通知。")
