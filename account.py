"""A股价值研投｜账号体系 V3

轻量会话账号 + SQLite 用户/会员映射 + 最近研究记录。
当前仍是原型：不保存密码、不接支付。
正式上线前应使用托管数据库与服务端认证体系。
"""
from __future__ import annotations

import re
import streamlit as st

from commercial_guard import is_pro, SESSION_PLAN_KEY
from user_store import get_membership, recent_research, upsert_user

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


def _render_history(account) -> None:
    rows = recent_research(account.get("user_id", ""), limit=8)
    if not rows:
        st.caption("最近还没有成功完成的研究记录。")
        return
    table = []
    for row in rows:
        try:
            score = "暂无" if row.get("score") is None else f"{float(row['score']):.0f}"
        except (TypeError, ValueError):
            score = "暂无"
        try:
            price = "暂无" if row.get("price") is None else f"{float(row['price']):.2f}"
        except (TypeError, ValueError):
            price = "暂无"
        try:
            normal_value = "暂无" if row.get("normal_value") is None else f"{float(row['normal_value']):.2f}"
        except (TypeError, ValueError):
            normal_value = "暂无"
        table.append(
            {
                "股票": f"{row.get('name') or row.get('code')} ({row.get('code')})",
                "评分": score,
                "决策": row.get("decision") or "暂无",
                "当前价": price,
                "合理价": normal_value,
                "研究时间": str(row.get("created_at", ""))[:19].replace("T", " "),
            }
        )
    st.dataframe(table, use_container_width=True, hide_index=True)


def render_account_panel() -> None:
    account = current_account()
    refresh_membership()
    plan = "专业会员" if is_pro() else "免费版"
    if account:
        st.caption(f"👤 {account.get('display_name', '用户')} · {account.get('email', '')} · {plan}")
        with st.expander("📚 最近研究记录", expanded=False):
            _render_history(account)
        if st.button("退出账号", key="vs_account_logout"):
            logout()
            st.rerun()
        return

    with st.expander("👤 登录 / 创建账号", expanded=False):
        st.caption("当前为 V3 原型：账号进入用户数据层，后续可承接研究历史与会员权益。不保存密码，不接入支付。")
        email = st.text_input("邮箱", placeholder="例如：you@example.com", key="vs_account_email")
        display_name = st.text_input("昵称（可选）", placeholder="例如：价值投资者", key="vs_account_name")
        if st.button("进入A股价值研投", type="primary", use_container_width=True, key="vs_account_login"):
            if login(email, display_name):
                st.success("✅ 账号状态已建立")
                st.rerun()
            else:
                st.error("请输入有效邮箱地址")
