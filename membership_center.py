"""A股价值研投｜会员中心 V3
会员展示层：账号、权益、微信 Native 付款二维码与订单状态核验。
"""
from __future__ import annotations

from io import BytesIO

import qrcode
import streamlit as st

from commercial_guard import is_pro, trial_status
from membership import plan_catalog
from user_store import get_membership
from payment import create_order, load_payment_config, query_order

ACCOUNT_KEY = "vs_account"
PAY_ORDER_KEY = "vs_payment_order_no"
PAY_QR_KEY = "vs_payment_qr"
PRO_PRICE_YUAN = 99


def _current_account():
    value = st.session_state.get(ACCOUNT_KEY)
    return value if isinstance(value, dict) else None


def _show_qr(value: str):
    img = qrcode.make(value)
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf.getvalue(), width=220)


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
            if card["plan"] != "pro":
                continue
            if plan == "pro":
                st.success("当前已是专业会员")
                continue

            st.markdown(f"**专业会员：¥{PRO_PRICE_YUAN}/月**")
            cfg = load_payment_config()
            if cfg.ready and account:
                if st.button("💳 微信支付开通", type="primary", use_container_width=True, key="vs_member_pay"):
                    order = create_order(account.get("user_id", ""), "pro", PRO_PRICE_YUAN * 100)
                    if order.get("ok"):
                        st.session_state[PAY_ORDER_KEY] = order.get("order_no")
                        st.session_state[PAY_QR_KEY] = order.get("code_url")
                        st.success("✅ 订单创建成功，请使用微信扫描下方二维码支付。")
                    else:
                        st.error(order.get("message", "微信下单失败。"))

                code_url = st.session_state.get(PAY_QR_KEY)
                order_no = st.session_state.get(PAY_ORDER_KEY)
                if code_url:
                    _show_qr(code_url)
                    st.caption(f"订单号：{order_no}")
                    if st.button("🔄 查询支付状态", use_container_width=True, key="vs_member_pay_check"):
                        status_result = query_order(order_no)
                        if status_result.get("paid"):
                            st.success(status_result.get("message", "支付成功，会员已开通。"))
                            st.rerun()
                        else:
                            st.info(status_result.get("message", "尚未确认支付成功。"))
            else:
                st.button("💳 微信支付开通｜待配置", disabled=True, use_container_width=True, key="vs_member_pay_disabled")
                st.caption("配置微信商户号、APPID、API v3 Key、商户证书与 HTTPS 回调地址后启用。")

    st.caption("支付采用微信官方 Native V3 下单；会员开通以微信官方订单查询结果为准。生产环境仍应增加异步回调、订单幂等、托管数据库与风控。")
