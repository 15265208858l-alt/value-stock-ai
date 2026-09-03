"""A股价值研投｜会员中心独立页面

统一复用会员中心商业组件，避免主页面与侧边页面出现两套价格、支付逻辑和 Widget Key。
"""
from __future__ import annotations

import streamlit as st

from membership_center import render_membership_center

st.set_page_config(page_title="会员中心 | A股价值研投", page_icon="💎", layout="wide")

st.markdown(
    """
    <style>
    .block-container{max-width:1000px;padding-top:1.2rem;padding-bottom:3rem}
    @media(max-width:768px){.block-container{padding:.55rem .7rem 2rem!important}}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("💎 A股价值研投 · 会员中心")
st.caption("账号、会员权益、微信 Native 支付与支付状态核验统一由商业化会员组件提供。")
render_membership_center()
st.caption("A股价值研投｜ValueStock AI · 研究工具仅用于信息分析，不构成投资建议。")
