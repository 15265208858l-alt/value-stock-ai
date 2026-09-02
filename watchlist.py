"""A股价值研投｜我的股票池 V1（商业层原型）

该模块与核心研究引擎隔离。
当前版本仅使用 Streamlit session state 保存股票池，适合产品原型验证；
正式商业化前应迁移到服务端数据库，并通过用户身份做权限控制。
"""

from __future__ import annotations

import re
from typing import Dict, List

import streamlit as st


SESSION_KEY = "vs_watchlist"
MAX_STOCKS = 20


def _clean_code(value: str) -> str:
    code = re.sub(r"\D", "", str(value or ""))
    return code if len(code) == 6 else ""


def _get_items() -> List[str]:
    items = st.session_state.get(SESSION_KEY, [])
    if not isinstance(items, list):
        return []
    return [str(x) for x in items if re.fullmatch(r"\d{6}", str(x))]


def add_stock(code: str) -> bool:
    code = _clean_code(code)
    if not code:
        return False
    items = _get_items()
    if code in items:
        return True
    if len(items) >= MAX_STOCKS:
        return False
    items.append(code)
    st.session_state[SESSION_KEY] = items
    return True


def remove_stock(code: str) -> None:
    code = _clean_code(code)
    st.session_state[SESSION_KEY] = [x for x in _get_items() if x != code]


def clear_watchlist() -> None:
    st.session_state[SESSION_KEY] = []


def get_watchlist() -> List[str]:
    return list(_get_items())


def render_watchlist() -> None:
    """渲染股票池 UI。默认允许访客使用，正式版需接入会员权限。"""
    st.markdown("---")
    st.subheader("⭐ 我的股票池")
    st.caption("保存你重点研究的A股代码，当前为本地会话版；正式会员版将升级为跨设备云端股票池。")

    items = get_watchlist()
    if items:
        cols = st.columns(min(4, max(1, len(items))))
        for i, code in enumerate(items):
            with cols[i % len(cols)]:
                st.markdown(f"**{code}**")
                if st.button("移除", key=f"vs_wl_remove_{code}", use_container_width=True):
                    remove_stock(code)
                    st.rerun()
    else:
        st.info("📌 股票池还是空的。研究完成后，把重点公司加入这里，后续可扩展估值提醒与跟踪。")

    with st.expander("＋ 添加股票到股票池", expanded=False):
        code_input = st.text_input("股票代码", placeholder="例如：000333", key="vs_watchlist_add_code")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("加入股票池", key="vs_watchlist_add", use_container_width=True):
                if add_stock(code_input):
                    st.success("✅ 已加入股票池")
                    st.rerun()
                else:
                    st.warning(f"请输入有效6位A股代码，且股票池最多保存{MAX_STOCKS}只。")
        with c2:
            if st.button("清空股票池", key="vs_watchlist_clear", use_container_width=True):
                clear_watchlist()
                st.rerun()

    st.caption("🔐 商业化说明：当前股票池仅保存在本次浏览会话。正式付费版本将采用服务端账户、数据库与权限校验，不在浏览器侧保存支付敏感信息。")
