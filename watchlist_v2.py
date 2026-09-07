"""A股价值研投｜我的股票池 V9
商业层模块：账号持久化 + 最近研究恢复 + 轻量行情跟踪 + 价格提醒 + 研究报告。
不修改核心研究引擎。
"""
from __future__ import annotations
import re,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from typing import Any,Dict,List
import pandas as pd
import streamlit as st
from valuation_alert import evaluate_alert,remove_alert,set_alert
from research_report import build_research_report
from commercial_guard import is_pro
from fast_data import load_watchlist_quotes
from user_store import add_watchlist_stock,clear_watchlist as clear_db_watchlist,get_watchlist as get_db_watchlist,remove_watchlist_stock,latest_research_for_codes,recent_research

WATCHLIST_KEY="vs_watchlist"; SNAPSHOT_KEY="vs_research_snapshots"; MAX_STOCKS=20; ACCOUNT_KEY="vs_account"; QUOTE_CACHE_KEY="vs_watchlist_quotes"; QUOTE_TTL=120; WATCHLIST_OPEN_KEY="vs_watchlist_open"

def _clean_code(v:Any)->str:
    code=re.sub(r"\D","",str(v or ""));return code if len(code)==6 else ""
def _user_id()->str:
    a=st.session_state.get(ACCOUNT_KEY);return str(a.get("user_id","")) if isinstance(a,dict) else ""
def get_watchlist()->List[str]:
    uid=_user_id()
    if uid:
        x=get_db_watchlist(uid,MAX_STOCKS);st.session_state[WATCHLIST_KEY]=x;return x
    x=st.session_state.get(WATCHLIST_KEY,[]);return [str(v) for v in x if re.fullmatch(r"\d{6}",str(v))]
def add_stock(code:str)->bool:
    if not is_pro() or not _user_id():return False
    code=_clean_code(code)
    if not code:return False
    ok=add_watchlist_stock(_user_id(),code,MAX_STOCKS)
    if ok:st.session_state[WATCHLIST_KEY]=get_db_watchlist(_user_id(),MAX_STOCKS)
    return ok
def remove_stock(code:str)->None:
    if not is_pro():return
    uid=_user_id();code=_clean_code(code)
    if uid:remove_watchlist_stock(uid,code);st.session_state[WATCHLIST_KEY]=get_db_watchlist(uid,MAX_STOCKS)
def clear_watchlist()->None:
    if not is_pro():return
    uid=_user_id()
    if uid:clear_db_watchlist(uid)
    st.session_state[WATCHLIST_KEY]=[]
def _snapshots()->Dict[str,Dict[str,Any]]:
    x=st.session_state.get(SNAPSHOT_KEY,{})
    return x if isinstance(x,dict) else {}
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
def _to_float(v):
    try:return float(str(v).strip()) if str(v).strip() else None
    except:return None

def refresh_quotes(items:List[str])->int:
    if not items:return 0
    quotes=load_watchlist_quotes(tuple(items));cache=st.session_state.setdefault(QUOTE_CACHE_KEY,{})
    count=0;now=time.time()
    for code,q in quotes.items():
        cache[code]=(now,{"price":q.get("最新价"),"change":q.get("涨跌幅"),"name":q.get("名称",code)})
        if q.get("最新价") is not None:count+=1
    st.session_state[QUOTE_CACHE_KEY]=cache
    return count

def _status(s):
    d=s.get("decision","");r=s.get("risk_level","");v=s.get("valuation_level","")
    if "回避" in d or "高风险" in r:return "🔴 高风险"
    if "建仓" in d or "试探" in d:return "🟢 可研究"
    if "等待" in d or "高估" in v:return "🟡 等待"
    if "观察" in d:return "🟠 观察"
    return "⚪ 数据不足"

def _alert_editor(code,s):
    if not is_pro():st.info("🔒 价格提醒属于 Pro 功能。升级后即可设置建仓价/重仓价。");return
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
    if not is_pro():st.info("🔒 专业研究报告为 Pro 功能。升级后可导出研究报告。");return
    report=build_research_report(s);name=str(s.get("name",code)).replace("/","_")
    st.download_button("📄 下载价值研究报告",report.encode("utf-8"),f"A股价值研投_{code}_{name}_研究报告.md","text/markdown",use_container_width=True,key=f"vs_report_{code}")

def _research_rank(rows):
    latest={}
    for row in rows or []:
        code=_clean_code(row.get("code"))
        if code and code not in latest:latest[code]=dict(row)
    ranked=[]
    for row in latest.values():
        score=_to_float(row.get("score"));margin=_to_float(row.get("safety_margin"))
        if score is None and margin is None:continue
        row["rank_score"]=(margin if margin is not None else -999)*0.6+(score if score is not None else 0)*0.4;ranked.append(row)
    return sorted(ranked,key=lambda x:x.get("rank_score",-999),reverse=True)

def render_free_rank_preview():
    uid=_user_id()
    if not uid or is_pro():return
    rows=_research_rank(recent_research(uid,limit=20));st.markdown("### 🏆 最近研究智能排行");st.caption("免费版展示最近研究股票 Top 3；不重新运行完整研究，不消耗额外数据链路。")
    if not rows:st.info("📌 先完成至少1只股票的价值研究，这里会自动形成你的智能排行。");return
    preview=[]
    for i,row in enumerate(rows[:3],1):preview.append({"排名":f"Top {i}","股票":f"{row.get('name') or row.get('code')} ({row.get('code')})","评分":_fmt(row.get("score")),"安全边际":_fmt(row.get("safety_margin"),"%"),"合理价":_fmt(row.get("normal_value")),"当前价":_fmt(row.get("price")),"结论":row.get("decision") or "暂无"})
    st.dataframe(pd.DataFrame(preview),use_container_width=True,hide_index=True);st.info("⭐ Pro 升级后可把重点股票加入20只股票池，并获得行情跟踪、价格提醒、研究报告。")

def render_watchlist_dashboard():
    if WATCHLIST_OPEN_KEY not in st.session_state:st.session_state[WATCHLIST_OPEN_KEY]=False
    if not st.session_state[WATCHLIST_OPEN_KEY]:
        st.markdown("---");st.markdown("### ⭐ 我的股票池 · 自动跟踪");st.caption("账号已保存的重点股票、轻量行情跟踪、估值提醒与研究报告。")
        if st.button("📂 查看我的股票池",key="vs_wl_open_v10_2",use_container_width=True):st.session_state[WATCHLIST_OPEN_KEY]=True;st.rerun()
        return
    st.markdown("---");st.subheader("⭐ 我的股票池 · 自动跟踪")
    if not _user_id():st.warning("👤 请先登录账号。");return
    if not is_pro():
        st.info("🔒 当前为免费版：可以进入并查看我的股票池页面。新增股票、持续行情跟踪、价格提醒、研究报告等功能属于 Pro。")
        render_free_rank_preview()
    items=get_watchlist();snaps=_load_persisted_snapshots(items)
    if items:
        if is_pro():
            top1,top2=st.columns([3,1])
            with top1:st.caption("研究结果来自账号历史；行情默认读取轻量缓存，点击刷新才主动更新。")
            with top2:
                if st.button("🔄 刷新行情",key="vs_wl_v9_refresh",use_container_width=True):
                    with st.spinner("正在刷新股票池行情…"):n=refresh_quotes(items)
                    st.success(f"已更新 {n}/{len(items)} 只股票");st.rerun()
        rows=[];cache=st.session_state.get(QUOTE_CACHE_KEY,{})
        for code in items:
            s=snaps.get(code,{});q=cache.get(code,({},{}))[1];price=q.get("price") or s.get("price");normal=s.get("normal_value");margin=None if price is None or normal in (None,0) else (float(normal)/float(price)-1)*100;change=q.get("change")
            rows.append({"股票":f"{s.get('name') or q.get('name') or code} ({code})","最新价":_fmt(price),"今日涨跌":_fmt(change,"%"),"评分":_fmt(s.get("score")),"评级":s.get("rating","未研究"),"合理价":_fmt(normal),"安全边际":_fmt(margin,"%"),"估值":s.get("valuation_level","未研究"),"风险":s.get("risk_level","未研究"),"提醒":evaluate_alert(code,price),"跟踪状态":_status(s) if s else "⚪ 尚未研究"})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        if is_pro():st.caption("⚡ 股票池行情仅调用轻量行情接口，不重新执行完整财务/估值研究。")
        with st.expander("🔔 设置价格提醒"):
            target=st.selectbox("选择股票",items,format_func=lambda x:f"{snaps.get(x,{}).get('name',x)} ({x})",key="vs_alert_target_v9");_alert_editor(target,snaps.get(target,{}))
        with st.expander("📄 生成研究报告"):
            target=st.selectbox("选择股票",items,format_func=lambda x:f"{snaps.get(x,{}).get('name',x)} ({x})",key="vs_report_target_v9");render_research_report_panel(target,snaps.get(target,{}))
        if is_pro() and st.button("清空股票池",key="vs_wl_v9_clear",use_container_width=True):clear_watchlist();st.rerun()
    else:st.info("📌 当前股票池为空。Pro 用户可添加最多20只重点股票进行持续跟踪。")
    with st.expander("＋ 添加/移除股票"):
        if not is_pro():st.warning("🔒 添加/移除股票属于 Pro 功能。升级后即可管理股票池。")
        else:
            code=st.text_input("股票代码",placeholder="例如：000333",key="vs_wl_v9_code");c1,c2=st.columns(2)
            with c1:
                if st.button("加入股票池",key="vs_wl_v9_add",use_container_width=True):
                    if add_stock(code):st.success("✅ 已加入并保存到账号");st.rerun()
                    else:st.warning(f"请输入有效6位A股代码，股票池最多{MAX_STOCKS}只。")
            with c2:
                rm=st.text_input("移除代码",placeholder="例如：000333",key="vs_wl_v9_rm")
                if st.button("移除",key="vs_wl_v9_remove",use_container_width=True):
                    if rm in get_watchlist():remove_stock(rm);st.success("✅ 已移除");st.rerun()
                    else:st.info("该股票不在当前股票池。")
    if st.button("收起股票池",key="vs_wl_close_v10_2",use_container_width=True):st.session_state[WATCHLIST_OPEN_KEY]=False;st.rerun()
    st.caption("🔐 V9：账号持久化 + 轻量行情跟踪；核心价值研究链路保持独立。")
