"""A股价值研投｜估值提醒 V2

商业层提醒：Pro 用户的提醒绑定账号并持久化到 SQLite；不发送外部消息。
"""
from __future__ import annotations
from typing import Any, Dict, Optional
import streamlit as st
from user_store import delete_valuation_alert, get_valuation_alerts, save_valuation_alert

ALERTS_KEY="vs_valuation_alerts"
ACCOUNT_KEY="vs_account"

def _user_id()->str:
    a=st.session_state.get(ACCOUNT_KEY)
    return str(a.get("user_id","")) if isinstance(a,dict) else ""

def _alerts()->Dict[str,Dict[str,Any]]:
    uid=_user_id()
    if uid:
        data=get_valuation_alerts(uid);st.session_state[ALERTS_KEY]=data;return data
    value=st.session_state.get(ALERTS_KEY,{})
    return value if isinstance(value,dict) else {}

def set_alert(code:str,entry_price:Optional[float],heavy_price:Optional[float])->None:
    code=str(code or "").strip()
    if not code:return
    uid=_user_id()
    if uid:save_valuation_alert(uid,code,entry_price,heavy_price)
    alerts=_alerts();alerts[code]={"entry_price":entry_price,"heavy_price":heavy_price};st.session_state[ALERTS_KEY]=alerts

def remove_alert(code:str)->None:
    code=str(code or "").strip();uid=_user_id()
    if uid:delete_valuation_alert(uid,code)
    alerts=_alerts();alerts.pop(code,None);st.session_state[ALERTS_KEY]=alerts

def evaluate_alert(code:str,price:Any)->str:
    alert=_alerts().get(str(code or "").strip())
    try:p=float(price)
    except (TypeError,ValueError):return "⚪ 当前价格暂无"
    if not alert:return "⚪ 未设置提醒"
    try:
        heavy=alert.get("heavy_price");entry=alert.get("entry_price")
        if heavy is not None and p<=float(heavy):return "🔴 已达到重仓参考价"
        if entry is not None and p<=float(entry):return "🟢 已达到建仓参考价"
    except (TypeError,ValueError):pass
    return "🟡 尚未触发"

def render_alert_panel(code:str,price:Any,entry_price:Any,heavy_price:Any)->None:
    st.subheader("🔔 估值提醒")
    st.caption("设置建仓价与重仓价。登录账号后提醒会自动保存，下次登录仍可继续使用。")
    current=_alerts().get(str(code or "").strip(),{})
    saved_entry=current.get("entry_price",entry_price);saved_heavy=current.get("heavy_price",heavy_price)
    c1,c2=st.columns(2)
    with c1:entry_text=st.text_input("建仓提醒价（元）",value="" if saved_entry is None else str(saved_entry),key=f"alert_entry_{code}")
    with c2:heavy_text=st.text_input("重仓提醒价（元）",value="" if saved_heavy is None else str(saved_heavy),key=f"alert_heavy_{code}")
    a,b=st.columns(2)
    with a:
        if st.button("保存提醒",key=f"alert_save_{code}",use_container_width=True):
            def num(x):
                try:return float(x) if str(x).strip() else None
                except (TypeError,ValueError):return None
            set_alert(code,num(entry_text),num(heavy_text));st.success("✅ 提醒已保存到账号");st.rerun()
    with b:
        if st.button("删除提醒",key=f"alert_remove_{code}",use_container_width=True):remove_alert(code);st.success("✅ 提醒已删除");st.rerun()
    st.info(evaluate_alert(code,price))
    st.caption("🔐 当前只做站内状态判断，不发送短信、微信或邮件。")
