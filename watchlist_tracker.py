"""A股价值研投｜股票池轻量跟踪层 V1

只读取股票池代码 + 最近研究快照，再通过 fast_data 的轻量历史接口获取最新行情。
不重新运行完整财务研究链，不修改核心研究引擎。
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable

import streamlit as st
import pandas as pd

from fast_data import _history, get_latest_price
from valuation_alert import evaluate_alert
from user_store import get_watchlist
from commercial_guard import is_pro

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
    snapshot = _snapshots().get(code, {})
    try:
        history = _history(code)
        price = get_latest_price(history)
    except Exception:
        price = None
    old_price = snapshot.get("price")
    change = None
    try:
        if old_price not in (None, "") and price is not None and float(old_price) != 0:
            change = (float(price) / float(old_price) - 1) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        pass

    normal = snapshot.get("normal_value")
    gap = None
    try:
        if normal not in (None, "") and price is not None and float(price) != 0:
            gap = (float(normal) / float(price) - 1) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        pass

    return {
        "代码": code,
        "名称": snapshot.get("name", code),
        "最新价": price,
        "较上次研究": change,
        "评分": snapshot.get("score"),
        "合理价": normal,
        "动态安全边际": gap,
        "投资决策": snapshot.get("decision", "未研究"),
        "估值判断": snapshot.get("valuation_level", "未研究"),
        "风险判断": snapshot.get("risk_level", "未研究"),
        "价格提醒": evaluate_alert(code, price),
        "研究状态": "已研究" if snapshot else "尚未研究",
    }


def load_tracking(codes: Iterable[str]) -> pd.DataFrame:
    codes = [str(x) for x in list(codes)[:MAX_TRACK]]
    if not codes:
        return pd.DataFrame()
    results: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(5, len(codes))) as ex:
        futures = {ex.submit(_one, code): code for code in codes}
        for future in as_completed(futures):
            code = futures[future]
            try:
                results[code] = future.result()
            except Exception:
                results[code] = _one(code)
    return pd.DataFrame([results[c] for c in codes if c in results])


def render_watchlist_tracking() -> None:
    if not is_pro() or not _user_id():
        return
    codes = get_watchlist(_user_id(), MAX_TRACK)
    if not codes:
        return
    st.markdown("### 📡 股票池动态跟踪")
    st.caption("仅刷新最新价格并重新计算安全边际；不会重新跑完整财务研究，因此速度更快。")
    if st.button("🔄 刷新股票池行情", key="vs_tracker_refresh", use_container_width=True):
        st.rerun()
    df = load_tracking(codes)
    if df.empty:
        st.info("暂无可用行情数据。")
        return
    display = df.copy()
    for col in ["最新价", "较上次研究", "评分", "合理价", "动态安全边际"]:
        if col in display.columns:
            display[col] = pd.to_numeric(display[col], errors="coerce")
    st.dataframe(display.round(2), use_container_width=True, hide_index=True)
    st.caption("提示：动态安全边际 = 最近一次研究的中性合理价 ÷ 最新价 − 1。合理价本身不会因刷新行情而改变。")
