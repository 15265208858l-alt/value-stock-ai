"""A股价值研投｜会员中心 V2
商业展示层：展示账号、会员权益与升级入口，并预留微信支付入口。
"""
from __future__ import annotations

import streamlit as st

from commercial_guard import is_pro, trial_status
from membership import plan_catalog
from user_store import get_membership
from payment import create_order, load_payment_config

ACCOUNT_KEY = "vs_account"
PRO_PRICE_YUAN = 99


def _current_account():
    value = st.session_state.get(ACCOUNT_KEY)
    return value if isinstance(value, dict) else None


def render_membership_center() -> None:
    account = _current_account()
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
                    st.markdown(f"**专业会员：¥{PRO_PRICE_YUAN}/月**")
                    cfg = load_payment_config()
                    if cfg.ready and account:
                        if st.button("💳 微信支付开通", type="primary", use_container_width=True, key="vs_member_pay"):
                            order = create_order(account.get("user_id", ""), "pro", PRO_PRICE_YUAN * 100)
                            if order.get("ok"):
                                st.success("支付订单已创建")
                            else:
                                st.info(order.get("message", "支付接口待完善"))
                    else:
                        st.button("💳 微信支付开通｜待配置", disabled=True, use_container_width=True, key="vs_member_pay_disabled")
                        st.caption("配置商户号、APPID、API v3 Key、商户证书与支付回调地址后启用。")

    st.caption("支付采用环境变量保存敏感参数；正式上线需接通微信官方下单、支付成功回调、订单核验与会员自动开通。")
