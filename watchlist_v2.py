"""A股价值研投｜我的股票池 V5
商业层模块：账号持久化 + 轻量行情跟踪，不修改核心研究引擎。"""
from __future__ import annotations
import re, time
from typing import Any, Dict, List
import pandas as pd
import streamlit as st
from valuation_alert import evaluate_alert, remove_alert, set_alert
from research_report import build_research_report
from commercial_guard import is_pro
from fast_data import load_stock_data_fast, get_latest_price
from user_store import add_watchlist_stock, clear_watchlist as clear_db_watchlist, get_watchlist as get_db_watchlist, remove_watchlist_stock

WATCHLIST_KEY="vs_watchlist"; SNAPSHOT_KEY="vs_research_snapshots"; MAX_STOCKS=20; ACCOUNT_KEY="vs_account"; QUOTE_CACHE_KEY="vs_watchlist_quotes"; QUOTE_TTL=300

def _clean_code(v:Any)->str:
    code=re.sub(r"\D","",str(v or "")); return code if len(code)==6 else ""
def _user_id()->str:
    a=st.session_state.get(ACCOUNT_KEY); return str(a.get("user_id","")) if isinstance(a,dict) else ""
def get_watchlist()->List[str]:
    uid=_user_id()
    if uid:
        x=get_db_watchlist(uid,MAX_STOCKS); st.session_state[WATCHLIST_KEY]=x; return x
    return [x for x in st.session_state.get(WATCHLIST_KEY,[]) if re.fullmatch(r"\d{6}",str(x))]
def add_stock(code:str)->bool:
    if not is_pro() or not _user_id(): return False
    code=_clean_code(code)
    if not code: return False
    ok=add_watchlist_stock(_user_id(),code,MAX_STOCKS)
    if ok: st.session_state[WATCHLIST_KEY]=get_db_watchlist(_user_id(),MAX_STOCKS)
    return ok
def remove_stock(code:str)->None:
    if not is_pro(): return
    code=_clean_code(code); uid=_user_id()
    if uid: remove_watchlist_stock(uid,code); st.session_state[WATCHLIST_KEY]=get_db_watchlist(uid,MAX_STOCKS)
def clear_watchlist()->None:
    if not is_pro(): return
    uid=_user_id()
    if uid: clear_db_watchlist(uid)
    st.session_state[WATCHLIST_KEY]=[]
def _snapshots()->Dict[str,Dict[str,Any]]:
    x=st.session_state.get(SNAPSHOT_KEY,{}); return x if isinstance(x,dict) else {}
def record_research_snapshot(**kwargs)->None:
    code=_clean_code(kwargs.get("code"))
    if not code:return
    s=_snapshots(); s[code]={"code":code,"name":str(kwargs.get("name") or code),"price":kwargs.get("price"),"score":kwargs.get("score"),"rating":str(kwargs.get("rating") or "暂无"),"decision":str(kwargs.get("decision") or "暂无"),"action":str(kwargs.get("action") or "暂无"),"position":str(kwargs.get("position") or "暂无"),"normal_value":kwargs.get("normal_value"),"safety_margin":kwargs.get("safety_margin"),"valuation_level":str(kwargs.get("valuation_level") or "数据不足"),"historical_level":str(kwargs.get("historical_level") or "数据不足"),"risk_level":str(kwargs.get("risk_level") or "数据不足")}; st.session_state[SNAPSHOT_KEY]=s
def _fmt(v,suffix=""):
    try:return "暂无" if v is None or v=="" else f"{float(v):.2f}{suffix}"
    except:return "暂无"
def _quote(code):
    cache=st.session_state.setdefault(QUOTE_CACHE_KEY,{ }); now=time.time(); old=cache.get(code)
    if old and now-old[0]<QUOTE_TTL:return old[1]
    try:
        data=load_stock_data_fast(code)
        q={"price":get_latest_price(data.get("history")) if data else None,"name":(data.get("market") or {}).get("名称",code) if data else code}
    except Exception:q={"price":None,"name":code}
    cache[code]=(now,q); return q
def _status(s):
    d=s.get("decision",""); r=s.get("risk_level",""); v=s.get("valuation_level","")
    if "回避" in d or "高风险" in r:return "🔴 高风险"
    if "建仓" in d or "试探" in d:return "🟢 可研究"
    if "等待" in d or "高估" in v:return "🟡 等待"
    if "观察" in d:return "🟠 观察"
    return "⚪ 数据不足"
def _to_float(v):
    try:return float(str(v).strip()) if str(v).strip() else None
    except:return None
def _alert_editor(code,s):
    current=st.session_state.get("vs_valuation_alerts",{}).get(code,{})
    a,b=st.columns(2)
    with a:entry=st.text_input("建仓提醒价",value="" if current.get("entry_price") is None else str(current.get("entry_price")),key=f"vs_alert_entry_{code}")
    with b:heavy=st.text_input("重仓提醒价",value="" if current.get("heavy_price") is None else str(current.get("heavy_price")),key=f"vs_alert_heavy_{code}")
    c,d=st.columns(2)
    with c:
        if st.button("保存",key=f"vs_alert_save_{code}",use_container_width=True):set_alert(code,_to_float(entry),_to_float(heavy));st.success("✅ 已保存");st.rerun()
    with d:
        if st.button("删除",key=f"vs_alert_del_{code}",use_container_width=True):remove_alert(code);st.success("✅ 已删除");st.rerun()
    st.caption(evaluate_alert(code,s.get("price")))
def render_research_report_panel(code,s):
    if not s:st.info("该股票尚未完成研究，暂无报告。");return
    if not is_pro():st.warning("🔒 专业研究报告为 Pro 功能。");return
    report=build_research_report(s); name=str(s.get("name",code)).replace("/","_"); st.download_button("📄 下载价值研究报告",report.encode("utf-8"),f"A股价值研投_{code}_{name}_研究报告.md","text/markdown",use_container_width=True,key=f"vs_report_{code}")
def render_watchlist_dashboard():
    st.markdown("---");st.subheader("⭐ 我的股票池 · 自动跟踪")
    if not is_pro():st.info("🔒 我的股票池为专业会员功能。免费版可体验核心研究，Pro 解锁持续跟踪、提醒和报告。");return
    if not _user_id():st.warning("👤 请先登录账号。");return
    items=get_watchlist(); snaps=_snapshots()
    if items:
        rows=[]
        for code in items:
            s=snaps.get(code,{ }); q=_quote(code); price=q.get("price"); normal=s.get("normal_value"); margin=None if price is None or normal in (None,0) else (float(normal)/float(price)-1)*100
            if s: s["price"]=price; s["safety_margin"]=margin
            rows.append({"股票":f"{s.get('name') or q.get('name') or code} ({code})","最新价":_fmt(price),"评分":_fmt(s.get("score")),"评级":s.get("rating","未研究"),"合理价":_fmt(normal),"安全边际":_fmt(margin,"%"),"估值":s.get("valuation_level","未研究"),"风险":s.get("risk_level","未研究"),"提醒":evaluate_alert(code,price),"跟踪状态":_status(s) if s else "⚪ 尚未研究"})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        st.caption("⚡ 行情采用5分钟轻量缓存；股票池不会触发完整20股深度研究。")
        with st.expander("🔔 设置价格提醒"):
            target=st.selectbox("选择股票",items,format_func=lambda x:f"{snaps.get(x,{}).get('name',x)} ({x})",key="vs_alert_target_v5");_alert_editor(target,snaps.get(target,{}))
        with st.expander("📄 生成研究报告"):
            target=st.selectbox("选择股票",items,format_func=lambda x:f"{snaps.get(x,{}).get('name',x)} ({x})",key="vs_report_target_v5");render_research_report_panel(target,snaps.get(target,{}))
        c1,c2=st.columns(2)
        with c1:
            if st.button("清空股票池",key="vs_wl_v5_clear",use_container_width=True):clear_watchlist();st.rerun()
        with c2:st.caption("完成研究后，最新研究结果会自动进入该股票快照。")
    else:st.info("📌 股票池为空，添加你长期关注的公司吧。")
    with st.expander("＋ 添加/移除股票"):
        code=st.text_input("股票代码",placeholder="例如：000333",key="vs_wl_v5_code")
        c1,c2=st.columns(2)
        with c1:
            if st.button("加入股票池",key="vs_wl_v5_add",use_container_width=True):
                if add_stock(code):st.success("✅ 已加入并保存到账号");st.rerun()
                else:st.warning(f"请输入有效6位A股代码，股票池最多{MAX_STOCKS}只。")
        with c2:
            rm=st.text_input("移除代码",placeholder="例如：000333",key="vs_wl_v5_rm")
            if st.button("移除",key="vs_wl_v5_remove",use_container_width=True):
                if rm in get_watchlist():remove_stock(rm);st.success("✅ 已移除");st.rerun()
                else:st.info("该股票不在当前股票池。")
    st.caption("🔐 股票池数据按账号保存；正式生产环境仍建议迁移托管数据库并接入服务端认证。")
