"""A股价值研投｜账号体系 V2

当前阶段：轻量会话账号 + SQLite 用户/会员映射原型。
不保存密码、不接支付、不把 session_state 当最终商业鉴权。
正式上线前应替换为服务端认证、数据库、密码哈希、验证码/风控与支付回调。
"""
from __future__ import annotations

import re
import streamlit as st

from commercial_guard import is_pro, SESSION_PLAN_KEY
from user_store import get_membership, upsert_user

ACCOUNT_KEY = "vs_account"


def _clean_email(value: str) -> str:
    value = str(value or "").strip().lower()
    return value if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value) else ""


def current_account():
    value = st.session_state.get(ACCOUNT_KEY)
    return value if isinstance(value, dict) else None


def login(email: str, display_name: str = "") -> bool:
    email = _clean_email(email)
    if not email:
        return False
    account = upsert_user(email, display_name)
    membership = get_membership(account["user_id"])
    st.session_state[ACCOUNT_KEY] = {
        "user_id": account["user_id"],
        "email": account["email"],
        "display_name": account["display_name"],
    }
    st.session_state[SESSION_PLAN_KEY] = membership.get("plan", "free")
    return True


def refresh_membership() -> None:
    account = current_account()
    if not account:
        st.session_state[SESSION_PLAN_KEY] = "free"
        return
    membership = get_membership(account.get("user_id", ""))
    st.session_state[SESSION_PLAN_KEY] = membership.get("plan", "free")


def logout() -> None:
    st.session_state.pop(ACCOUNT_KEY, None)
    st.session_state[SESSION_PLAN_KEY] = "free"


def render_account_panel() -> None:
    account = current_account()
    refresh_membership()
    plan = "专业会员" if is_pro() else "免费版"
    if account:
        st.caption(f"👤 {account.get('display_name', '用户')} · {account.get('email', '')} · {plan}")
        if st.button("退出账号", key="vs_account_logout"):
            logout()
            st.rerun()
        return

    with st.expander("👤 登录 / 创建账号", expanded=False):
        st.caption("当前为 V2 原型：账号信息进入本地用户数据层；不保存密码，不接入支付。")
        email = st.text_input("邮箱", placeholder="例如：you@example.com", key="vs_account_email")
        display_name = st.text_input("昵称（可选）", placeholder="例如：价值投资者", key="vs_account_name")
        if st.button("进入A股价值研投", type="primary", use_container_width=True, key="vs_account_login"):
            if login(email, display_name):
                st.success("✅ 账号状态已建立")
                st.rerun()
            else:
                st.error("请输入有效邮箱地址")
