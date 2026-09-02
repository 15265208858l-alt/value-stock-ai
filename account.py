"""A股价值研投｜账号体系 V1

当前阶段：轻量会话账号原型，不保存密码、不接支付。
正式上线前应替换为服务端认证、数据库、密码哈希、验证码/风控与支付回调。
"""
from __future__ import annotations

import re
import streamlit as st

from commercial_guard import is_pro

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
    st.session_state[ACCOUNT_KEY] = {
        "email": email,
        "display_name": str(display_name or email.split("@")[0]).strip() or email.split("@")[0],
    }
    return True


def logout() -> None:
    st.session_state.pop(ACCOUNT_KEY, None)


def render_account_panel() -> None:
    account = current_account()
    plan = "专业会员" if is_pro() else "免费版"
    if account:
        st.caption(f"👤 {account.get('display_name', '用户')} · {account.get('email', '')} · {plan}")
        if st.button("退出账号", key="vs_account_logout"):
            logout()
            st.rerun()
        return

    with st.expander("👤 登录 / 创建账号", expanded=False):
        st.caption("当前为 V1 原型：只保存会话身份，不保存密码，不接入支付。")
        email = st.text_input("邮箱", placeholder="例如：you@example.com", key="vs_account_email")
        display_name = st.text_input("昵称（可选）", placeholder="例如：价值投资者", key="vs_account_name")
        if st.button("进入A股价值研投", type="primary", use_container_width=True, key="vs_account_login"):
            if login(email, display_name):
                st.success("✅ 账号状态已建立")
                st.rerun()
            else:
                st.error("请输入有效邮箱地址")
