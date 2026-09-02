"""A股价值研投｜会员中心 V1
商业展示层：展示账号、会员权益与升级入口，不接支付。
"""
from __future__ import annotations

import streamlit as st

from commercial_guard import is_pro, trial_status
from membership import plan_catalog
from user_store import get_membership
from account import current_account


def render_membership_center() -> None:
    account = current_account()
    status = trial_status()
    plan = "pro" if is_pro() else "free"

    st.markdown("---")
    st.subheader("⭐ 会员中心")

    if account:
        membership = get_membership(account.get("user_id", ""))
        expires = membership.get("expires_at") or "未设置"
        a, b, c = st.columns(3)
        a.metric("当前账号", account.get("display_name") or "用户")
        b.metric("会员等级", "专业会员" if plan == "pro" else "免费版")
        c.metric("会员到期", expires if plan == "pro" else "—")
    else:
        st.info("👤 登录后可绑定你的研究历史与会员权益。")

    if plan == "free":
        remaining = status.get("remaining")
        st.warning(f"🎁 免费研究额度：{remaining if remaining is not None else 0} 只股票")

    cards = list(plan_catalog())
    left, right = st.columns(2)
    for container, card in zip((left, right), cards):
        with container:
            title = "⭐ " + card["name"] if card["plan"] == "pro" else "🆓 " + card["name"]
            st.markdown(f"**{title}**")
            st.caption(card["positioning"])
            for feature in card["features"]:
                st.write("✅ " + feature)
            if card["plan"] == "pro":
                if plan == "pro":
                    st.success("当前已是专业会员")
                else:
                    st.button("⭐ 专业会员｜即将开放", disabled=True, use_container_width=True, key="vs_member_upgrade")

    st.caption("当前阶段暂不接入支付。正式收费前将接入服务端订单、支付回调、会员到期校验与风控。")
