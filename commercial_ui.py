"""A股价值研投｜商业化 UI 层。

只负责产品展示与升级引导，不参与核心研究计算、评分或估值。
当前不接收任何支付信息，也不在前端保存敏感支付数据。
"""


def render_membership_entry():
    try:
        import streamlit as st
        from membership import get_membership, plan_catalog
        from commercial_guard import trial_status

        membership = get_membership()
        status = trial_status()

        st.markdown(
            """
            <style>
            .vs-plan-card{border:1px solid #e6dfd0;border-radius:16px;padding:16px;margin:12px 0;background:#fffdf8;}
            .vs-plan-title{font-size:1.02rem;font-weight:900;color:#7a5b22;}
            .vs-plan-sub{font-size:.78rem;color:#6b778c;margin-top:4px;line-height:1.5;}
            .vs-plan-features{font-size:.78rem;color:#4f5f73;line-height:1.7;margin-top:8px;}
            .vs-upgrade-note{font-size:.76rem;color:#65748a;margin-top:7px;}
            </style>
            """,
            unsafe_allow_html=True,
        )

        if membership.is_pro:
            st.success("⭐ 专业会员｜不限股票研究")
            return

        used = status.get("used", False)
        stock = status.get("trial_stock") or ""
        remaining = status.get("remaining", 1)

        if not used:
            st.info("🎁 免费体验：完整测试 1 只股票；同一只股票后续可重复查看。")
        else:
            st.warning(f"🎁 免费体验已使用：{stock or '已完成'}｜剩余新股票名额：{remaining}")

        plans = list(plan_catalog())
        pro = next((x for x in plans if x.get("plan") == "pro"), None)
        if pro:
            features = " · ".join(pro.get("features", []))
            st.markdown(
                f"""<div class="vs-plan-card"><div class="vs-plan-title">⭐ 专业会员</div>
                <div class="vs-plan-sub">{pro.get('positioning','持续跟踪重点股票，提升研究效率')}</div>
                <div class="vs-plan-features">{features}</div>
                <div class="vs-upgrade-note">正式收费前将完成账号、服务端权限、订单与支付回调的安全闭环。</div></div>""",
                unsafe_allow_html=True,
            )
            st.button("⭐ 专业会员｜即将开放", disabled=True, use_container_width=True)
    except Exception:
        return
