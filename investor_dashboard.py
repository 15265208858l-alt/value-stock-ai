"""A股价值研投｜个人投资驾驶舱 V12
仅使用已经保存的研究结果做展示，不重新运行核心研究，不修改估值与评分引擎。
"""
from __future__ import annotations

import streamlit as st

from commercial_guard import is_pro, trial_status
from user_store import recent_research

ACCOUNT_KEY = "vs_account"


def _account():
    value = st.session_state.get(ACCOUNT_KEY)
    return value if isinstance(value, dict) else None


def _num(value):
    try:
        if value is None or str(value).strip() in {"", "None", "nan", "NaN"}:
            return None
        return float(value)
    except Exception:
        return None


def _decision_text(value):
    return str(value or "—")


def render_investor_dashboard() -> None:
    """渲染首页个人投资驾驶舱。"""
    account = _account()
    if not account:
        return

    uid = account.get("user_id", "")
    rows = recent_research(uid, limit=20)
    pro = is_pro()
    status = trial_status()

    st.markdown("---")
    st.subheader("🧭 个人投资驾驶舱")
    st.caption("把最近研究、机会、安全边际和变化提醒集中到一处；只读取已保存结果，不重新运行核心研究。")

    latest = rows[0] if rows else None
    if latest:
        code = str(latest.get("code") or "—")
        name = str(latest.get("name") or code)
        score = _num(latest.get("score"))
        margin = _num(latest.get("safety_margin"))
        price = _num(latest.get("price"))
        normal = _num(latest.get("normal_value"))
        decision = _decision_text(latest.get("decision"))

        a, b, c, d = st.columns(4)
        a.metric("最近研究", f"{name} {code}")
        b.metric("综合评分", "—" if score is None else f"{score:.0f}/100")
        c.metric("安全边际", "—" if margin is None else f"{margin:.1f}%")
        d.metric("投资结论", decision)

        if price is not None and normal is not None and price > 0:
            live_margin = (normal / price - 1) * 100
            st.info(f"🎯 {name} 当前价 {price:.2f} 元｜合理价值 {normal:.2f} 元｜按最新保存结果计算的安全边际约 {live_margin:.1f}%")
    else:
        remaining = status.get("remaining")
        st.info(
            f"👋 你的投资驾驶舱已经准备好。当前还没有保存的研究结果；先研究一家公司，之后这里会自动形成你的个人研究台账。"
            f" 免费研究额度：{remaining if remaining is not None else 0} 只股票。"
        )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**🔥 机会雷达**")
        if rows:
            ranked = []
            for row in rows:
                margin = _num(row.get("safety_margin"))
                score = _num(row.get("score"))
                if margin is None and score is None:
                    continue
                radar = (margin or 0) * 0.6 + (score or 0) * 0.4
                ranked.append((radar, row))
            ranked.sort(key=lambda x: x[0], reverse=True)
            for idx, (_, row) in enumerate(ranked[:3], 1):
                st.write(f"{idx}. **{row.get('name') or row.get('code')}** · {row.get('decision') or '—'}")
        else:
            st.caption("完成首次研究后自动生成")

    with c2:
        st.markdown("**🔄 研究变化**")
        if rows:
            seen = set()
            shown = 0
            for row in rows:
                code = str(row.get("code") or "")
                if not code or code in seen:
                    continue
                seen.add(code)
                same = [x for x in rows if str(x.get("code") or "") == code]
                if len(same) < 2:
                    continue
                old, new = same[1], same[0]
                sd = (_num(new.get("score")) or 0) - (_num(old.get("score")) or 0)
                md = (_num(new.get("safety_margin")) or 0) - (_num(old.get("safety_margin")) or 0)
                if sd > 2 or md > 3:
                    icon = "🟢"
                elif sd < -2 or md < -3:
                    icon = "🔴"
                else:
                    icon = "🟡"
                st.write(f"{icon} **{new.get('name') or code}** · 评分 {sd:+.0f} · 安全边际 {md:+.1f}pct")
                shown += 1
                if shown >= 3:
                    break
            if shown == 0:
                st.caption("暂时没有第二次研究可比较")
        else:
            st.caption("完成首次研究后自动生成")

    with c3:
        st.markdown("**🔔 估值提醒**")
        alerts = []
        grouped = {}
        for row in rows:
            code = str(row.get("code") or "")
            if code and code not in grouped:
                grouped[code] = []
            if code:
                grouped[code].append(row)
        for code, items in grouped.items():
            if len(items) < 2:
                continue
            new, old = items[0], items[1]
            nv, ov = _num(new.get("normal_value")), _num(old.get("normal_value"))
            sm, osm = _num(new.get("safety_margin")), _num(old.get("safety_margin"))
            changes = []
            if nv is not None and ov not in (None, 0):
                pct = (nv / ov - 1) * 100
                if abs(pct) >= 5:
                    changes.append(f"合理价值 {pct:+.1f}%")
            if sm is not None and osm is not None and abs(sm - osm) >= 5:
                changes.append(f"安全边际 {sm-osm:+.1f}pct")
            if changes:
                alerts.append((new.get("name") or code, "；".join(changes)))
        limit = 5 if pro else 3
        if alerts:
            for name, text in alerts[:limit]:
                st.write(f"⚠️ **{name}** · {text}")
        else:
            st.caption("当前没有达到提醒阈值的明显变化")

    with st.expander("📚 最近研究台账", expanded=False):
        if rows:
            for row in rows[:8]:
                st.write(
                    f"**{row.get('name') or row.get('code')}**（{row.get('code') or '—'}）｜"
                    f"评分 {row.get('score') if row.get('score') is not None else '—'}｜"
                    f"安全边际 {row.get('safety_margin') if row.get('safety_margin') is not None else '—'}%｜"
                    f"{row.get('decision') or '—'}"
                )
        else:
            st.caption("暂无研究记录")

    if not pro:
        st.markdown("**⭐ 专业会员升级方向**")
        st.caption("专业会员将重点解锁更多股票跟踪、深度研究、估值提醒和个人投资管理能力。")
