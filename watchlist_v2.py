"""A股价值研投｜我的股票池 V7
商业层模块：账号持久化 + 最近研究恢复 + 手动轻量行情刷新。
不修改核心研究引擎。免费用户可进入页面查看功能，Pro 才可使用持续跟踪与管理功能。"""
from __future__ import annotations
import re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
import pandas as pd
import streamlit as st
from valuation_alert import evaluate_alert, remove_alert, set_alert
from research_report import build_research_report
from commercial_guard import is_pro
from fast_data import load_stock_data_fast, get_latest_price
from user_store import (add_watchlist_stock, clear_watchlist as clear_db_watchlist,
    get_watchlist as get_db_watchlist, remove_watchlist_stock, latest_research_for_codes)
WATCHLIST_KEY="vs_watchlist"; SNAPSHOT_KEY="vs_research_snapshots"; MAX_STOCKS=20
ACCOUNT_KEY="vs_account"; QUOTE_CACHE_KEY="vs_watchlist_quotes"; QUOTE_TTL=300

def _clean_code(v:Any)->str:
    code=re.sub(r"\D","",str(v or "")); return code if len(code)==6 else ""
def _user_id()->str:
    a=st.session_state.get(ACCOUNT_KEY); return str(a.get("user_id","")) if isinstance(a,dict) else ""
def get_watchlist()->List[str]:
    uid=_user_id()
    if uid:
        x=get_db_watchlist(uid,MAX_STOCKS); st.session_state[WATCHLIST_KEY]=x; return x
    x=st.session_state.get(WATCHLIST_KEY,[]); return [str(v) for v in x if re.fullmatch(r"\d{6}",str(v))]
def add_stock(code:str)->bool:
    if not is_pro() or not _user_id(): return False
    code=_clean_code(code)
    if not code:return False
    ok=add_watchlist_stock(_user_id(),code,MAX_STOCKS)
    if ok:st.session_state[WATCHLIST_KEY]=get_db_watchlist(_user_id(),MAX_STOCKS)
    return ok
def remove_stock(code:str)->None:
    if not is_pro():return
    code=_clean_code(code);uid=_user_id()
    if uid:remove_watchlist_stock(uid,code);st.session_state[WATCHLIST_KEY]=get_db_watchlist(uid,MAX_STOCKS)
def clear_watchlist()->None:
    if not is_pro():return
    uid=_user_id()
    if uid:clear_db_watchlist(uid)
    st.session_state[WATCHLIST_KEY]=[]
def _snapshots()->Dict[str,Dict[str,Any]]:
    x=st.session_state.get(SNAPSHOT_KEY,{ });return x if isinstance(x,dict) else {}
def record_research_snapshot(**kwargs)->None:
    code=_clean_code(kwargs.get("code"))
    if not code:return
    s=_snapshots();s[code]={"code":code,"name":str(kwargs.get("name") or code),"price":kwargs.get("price"),"score":kwargs.get("score"),"rating":str(kwargs.get("rating") or "暂无"),"decision":str(kwargs.get("decision") or "暂无"),"action":str(kwargs.get("action") or "暂无"),"position":str(kwargs.get("position") or "暂无"),"normal_value":kwargs.get("normal_value"),"safety_margin":kwargs.get("safety_margin"),"valuation_level":str(kwargs.get("valuation_level") or "数据不足"),"historical_level":str(kwargs.get("historical_level") or "数据不足"),"risk_level":str(kwargs.get("risk_level") or "数据不足")};st.session_state[SNAPSHOT_KEY]=s
def _load_persisted_snapshots(items:List[str])->Dict[str,Dict[str,Any]]:
    s=_snapshots();uid=_user_id()
    if uid:
        for code,row in latest_research_for_codes(uid,items).items():
            if code not in s:s[code]={"code":code,"name":row.get("name") or code,"price":row.get("price"),"score":row.get("score"),"rating":"暂无","decision":row.get("decision") or "暂无","action":"暂无","position":"暂无","normal_value":row.get("normal_value"),"safety_margin":row.get("safety_margin"),"valuation_level":"暂无","historical_level":"暂无","risk_level":"暂无"}
    st.session_state[SNAPSHOT_KEY]=s;return s
def _fmt(v,suffix=""):
    try:return "暂无" if v is None or v=="" else f"{float(v):.2f}{suffix}"
    except:return "暂无"
def _quote(code):
    cache=st.session_state.setdefault(QUOTE_CACHE_KEY,{});old=cache.get(code);now=time.time()
    if old and now-old[0]<QUOTE_TTL:return old[1]
    try:
        data=load_stock_data_fast(code);q={"price":get_latest_price(data.get("history")) if data else None,"name":(data.get("market") or {}).get("名称",code) if data else code}
    except Exception:q={"price":None,"name":code}
    cache[code]=(now,q);return q
def refresh_quotes(items:List[str])->int:
    if not items:return 0
    cache=st.session_state.setdefault(QUOTE_CACHE_KEY,{});count=0
    def one(code):return code,_quote(code)
    with ThreadPoolExecutor(max_workers=min(5,len(items))) as ex:
        futures=[ex.submit(one,c) for c in items]
        for f in as_completed(futures):
            try:
                code,q=f.result();cache[code]=(time.time(),q)
                if q.get("price") is not None:count+=1
            except Exception:pass
    st.session_state[QUOTE_CACHE_KEY]=cache;return count
def _status(s):
    d=s.get("decision","");r=s.get("risk_level","");v=s.get("valuation_level","")
    if "回避" in d or "高风险" in r:return "🔴 高风险"
    if "建仓" in d or "试探" in d:return "🟢 可研究"
    if "等待" in d or "高估" in v:return "🟡 等待"
    if "观察" in d:return "🟠 观察"
    return "⚪ 数据不足"
def _to_float(v):
    try:return float(str(v).strip()) if str(v).strip() else None
    except:return None
def _alert_editor(code,s):
    if not is_pro():
        st.info("🔒 价格提醒属于 Pro 功能。升级后即可设置建仓价/重仓价。")
        return
    current=st.session_state.get("vs_valuation_alerts",{}).get(code,{ });a,b=st.columns(2)
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
    if not is_pro():st.info("🔒 专业研究报告为 Pro 功能。升级后可导出研究报告。");return
    report=build_research_report(s);name=str(s.get("name",code)).replace("/","_")
    st.download_button("📄 下载价值研究报告",report.encode("utf-8"),f"A股价值研投_{code}_{name}_研究报告.md","text/markdown",use_container_width=True,key=f"vs_report_{code}")
def render_watchlist_dashboard():
    st.markdown("---");st.subheader("⭐ 我的股票池 · 自动跟踪")
    if not _user_id():
        st.warning("👤 请先登录账号。");return
    if not is_pro():
        st.info("🔒 当前为免费版：可以进入并查看我的股票池页面。新增股票、持续行情跟踪、价格提醒、研究报告等功能属于 Pro。")
        st.caption("💡 这是产品功能展示入口，不会因为会员权限而无法点击。")
    items=get_watchlist();snaps=_load_persisted_snapshots(items)
    if items:
        if is_pro():
            top1,top2=st.columns([3,1])
            with top1:st.caption("研究结果来自账号历史；行情默认读取最近缓存，点击刷新才主动更新。")
            with top2:
                if st.button("🔄 刷新行情",key="vs_wl_v7_refresh",use_container_width=True):
                    with st.spinner("正在刷新股票池行情…"):n=refresh_quotes(items)
                    st.success(f"已更新 {n}/{len(items)} 只股票");st.rerun()
        rows=[]
        for code in items:
            s=snaps.get(code,{ });q=st.session_state.get(QUOTE_CACHE_KEY,{}).get(code,({},{}))[1];price=q.get("price") or s.get("price");normal=s.get("normal_value");margin=None if price is None or normal in (None,0) else (float(normal)/float(price)-1)*100
            rows.append({"股票":f"{s.get('name') or q.get('name') or code} ({code})","最新价":_fmt(price),"评分":_fmt(s.get("score")),"评级":s.get("rating","未研究"),"合理价":_fmt(normal),"安全边际":_fmt(margin,"%"),"估值":s.get("valuation_level","未研究"),"风险":s.get("risk_level","未研究"),"提醒":evaluate_alert(code,price),"跟踪状态":_status(s) if s else "⚪ 尚未研究"})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        if is_pro():
            st.caption("⚡ 行情刷新使用现有 fast_data 缓存；不会重新执行20只股票的完整价值研究。")
        with st.expander("🔔 设置价格提醒"):
            target=st.selectbox("选择股票",items,format_func=lambda x:f"{snaps.get(x,{}).get('name',x)} ({x})",key="vs_alert_target_v7");_alert_editor(target,snaps.get(target,{}))
        with st.expander("📄 生成研究报告"):
            target=st.selectbox("选择股票",items,format_func=lambda x:f"{snaps.get(x,{}).get('name',x)} ({x})",key="vs_report_target_v7");render_research_report_panel(target,snaps.get(target,{}))
        if is_pro() and st.button("清空股票池",key="vs_wl_v7_clear",use_container_width=True):clear_watchlist();st.rerun()
    else:
        st.info("📌 当前股票池为空。Pro 用户可添加最多20只重点股票进行持续跟踪。")
    with st.expander("＋ 添加/移除股票"):
        if not is_pro():
            st.warning("🔒 添加/移除股票属于 Pro 功能。升级后即可管理股票池。")
        else:
            code=st.text_input("股票代码",placeholder="例如：000333",key="vs_wl_v7_code");c1,c2=st.columns(2)
            with c1:
                if st.button("加入股票池",key="vs_wl_v7_add",use_container_width=True):
                    if add_stock(code):st.success("✅ 已加入并保存到账号");st.rerun()
                    else:st.warning(f"请输入有效6位A股代码，股票池最多{MAX_STOCKS}只。")
            with c2:
                rm=st.text_input("移除代码",placeholder="例如：000333",key="vs_wl_v7_rm")
                if st.button("移除",key="vs_wl_v7_remove",use_container_width=True):
                    if rm in get_watchlist():remove_stock(rm);st.success("✅ 已移除");st.rerun()
                    else:st.info("该股票不在当前股票池。")
    st.caption("🔐 V7：股票池账号持久化已完成；会员权限仅限制具体商业功能，不阻断页面入口。")
