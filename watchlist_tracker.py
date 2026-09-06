"""A股价值研投｜股票池轻量跟踪层 V2
商业层模块：跟踪失败绝不影响主研究页面。"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable
import pandas as pd
import streamlit as st
from commercial_guard import is_pro
from fast_data import _history, get_latest_price
from user_store import get_watchlist
from valuation_alert import evaluate_alert

ACCOUNT_KEY = "vs_account"
SNAPSHOT_KEY = "vs_research_snapshots"
MAX_TRACK = 20

def _user_id() -> str:
    account = st.session_state.get(ACCOUNT_KEY)
    return str(account.get("user_id", "")) if isinstance(account, dict) else ""

def _snapshots() -> Dict[str, Dict[str, Any]]:
    value = st.session_state.get(SNAPSHOT_KEY, {})
    return value if isinstance(value, dict) else {}

def _one(code: str) -> Dict[str, Any]:
    code = str(code).strip()
    snapshot = _snapshots().get(code, {})
    try:
        price = get_latest_price(_history(code))
    except Exception:
        price = None
    def num(v):
        try: return float(v)
        except (TypeError, ValueError): return None
    current = num(price); old = num(snapshot.get("price")); normal = num(snapshot.get("normal_value"))
    change = None if old in (None, 0) or current is None else (current / old - 1) * 100
    gap = None if normal is None or current in (None, 0) else (normal / current - 1) * 100
    try: alert = evaluate_alert(code, current)
    except Exception: alert = "⚪ 当前价格暂无"
    return {"代码":code,"名称":snapshot.get("name") or code,"最新价":current,"较上次研究":change,"评分":num(snapshot.get("score")),"合理价":normal,"动态安全边际":gap,"投资决策":snapshot.get("decision") or "尚未研究","估值判断":snapshot.get("valuation_level") or "尚未研究","风险判断":snapshot.get("risk_level") or "尚未研究","价格提醒":alert,"研究状态":"已研究" if snapshot else "尚未研究"}

def load_tracking(codes: Iterable[str]) -> pd.DataFrame:
    codes = [str(x).strip() for x in list(codes)[:MAX_TRACK] if str(x).strip()]
    if not codes: return pd.DataFrame()
    results = {}
    try:
        with ThreadPoolExecutor(max_workers=min(5, len(codes))) as ex:
            futures = {ex.submit(_one, c): c for c in codes}
            for f in as_completed(futures):
                c = futures[f]
                try: results[c] = f.result()
                except Exception: results[c] = {"代码":c,"名称":c,"最新价":None,"较上次研究":None,"评分":None,"合理价":None,"动态安全边际":None,"投资决策":"暂无","估值判断":"暂无","风险判断":"暂无","价格提醒":"⚪ 当前价格暂无","研究状态":"尚未研究"}
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame([results[c] for c in codes if c in results])

def render_watchlist_tracking() -> None:
    try:
        if not is_pro(): return
        uid = _user_id()
        if not uid: return
        codes = get_watchlist(uid, MAX_TRACK)
        if not codes: return
        st.markdown("### 📡 股票池动态跟踪")
        st.caption("只刷新最新行情并动态计算安全边际，不重新运行完整财务研究。")
        if st.button("🔄 刷新股票池行情", key="vs_tracker_refresh_v2", use_container_width=True): st.rerun()
        df = load_tracking(codes)
        if df.empty:
            st.info("暂无可用行情数据，主研究功能不受影响。")
            return
        for col in ["最新价","较上次研究","评分","合理价","动态安全边际"]:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce")
        st.dataframe(df.round(2), use_container_width=True, hide_index=True)
        st.caption("动态安全边际 = 最近一次研究的中性合理价 ÷ 最新价 − 1。合理价不会因行情刷新自动改变。")
    except Exception as exc:
        st.info("📡 股票池跟踪暂时不可用，但不会影响主研究。")
        st.caption(f"跟踪模块已自动降级：{type(exc).__name__}")
