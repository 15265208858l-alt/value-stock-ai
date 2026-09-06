import streamlit as st
import pandas as pd

from fast_data import clean_stock_code, load_stock_data_fast, load_peer_snapshots, check_data_completeness, get_latest_price
from financial import process_financial_indicators, calculate_financial_quality
from risk import analyze_financial_risk
from valuation import calculate_valuation_scenarios, calculate_eps_cagr, build_growth_sensitivity
from adaptive_valuation import detect_valuation_model, get_valuation_config
from earnings_basis import build_earnings_basis
from growth_quality import calculate_growth_quality, get_dynamic_growth_pe
from historical_valuation import build_historical_pe, calculate_historical_statistics, get_historical_valuation_level
from peer_compare import calculate_peer_score, build_peer_summary, compare_target_with_average
from investment_score import calculate_investment_score
from investment_decision import make_investment_decision
from industry import get_peer_candidates, get_stock_name
from commercial_guard import install_ui_notice
from account import current_account, render_account_panel
from user_store import save_research_snapshot
from membership_center import render_membership_center
from watchlist_v2 import render_watchlist_dashboard, record_research_snapshot
from watchlist_tracker import render_watchlist_tracking

st.set_page_config(page_title="A股价值研投 | ValueStock AI", page_icon="📈", layout="wide")

st.markdown("""
<style>
body { background:#fafafa; }
.vs-result { padding:18px; border-radius:14px; margin:10px 0 18px 0; border:1px solid #ddd; }
.vs-result-title { font-size:18px; font-weight:700; }
.vs-result-main { font-size:25px; font-weight:800; margin:8px 0; }
.vs-result-sub { font-size:14px; line-height:1.8; }
.vs-result-good { border-left:6px solid #198754; }
.vs-result-mid { border-left:6px solid #f0ad00; }
.vs-result-bad { border-left:6px solid #dc3545; }
.vs-company { font-size:25px; font-weight:800; margin-top:8px; }
.vs-badge { font-size:13px; border:1px solid #ddd; border-radius:20px; padding:4px 10px; }
.vs-explain { line-height:1.8; }
@media (max-width: 768px) {
  .block-container { padding: 1rem 0.75rem 2rem 0.75rem; }
  h1 { font-size: 1.7rem !important; }
  h2 { font-size: 1.35rem !important; }
  h3 { font-size: 1.15rem !important; }
}
</style>
""", unsafe_allow_html=True)

st.title("📈 A股价值研投")
st.caption("ValueStock AI｜用AI研究价值，而不是追逐情绪。")

install_ui_notice()
render_account_panel()

code_input = st.text_input("请输入A股代码", value="000333", max_chars=6, key="stock_code_input")
code = clean_stock_code(code_input)
start = st.button("🔍 开始价值研究", type="primary", use_container_width=True)

if start:
    if not code:
        st.error("请输入6位A股代码")
        st.stop()
    data = load_stock_data_fast(code)
    if not data:
        st.error("股票数据获取失败，请稍后重试")
        st.stop()

    market = data.get("market") or {}
    name = market.get("名称") or get_stock_name(code) or code
    price = market.get("最新价") or get_latest_price(data.get("history"))
    st.header("📌 一、目标股票")
    a,b,c = st.columns(3)
    a.metric("股票", f"{name} ({code})")
    b.metric("最新价", "暂无" if price is None else f"{price:.2f} 元")
    c.metric("数据完整度", f"{check_data_completeness(data)['score']}%")

    fin = process_financial_indicators(data.get("indicators"), stock_code=code)
    fq = calculate_financial_quality(fin.get("trend"), cashflow_ratio=None)
    st.header("💰 二、财务质量")
    st.write(f"财务质量评分：**{fq.get('score','暂无')}/30**")
    if fin.get("annual"):
        st.dataframe(pd.DataFrame([fin["annual"]]), use_container_width=True, hide_index=True)

    risk = analyze_financial_risk(data.get("balance"), data.get("profit"), data.get("cashflow"), fin)
    risk_score = risk.get("score")
    st.header("⚠️ 三、财务风险")
    st.write(f"风险评分：**{risk_score if risk_score is not None else '暂无'}**")
    for item in risk.get("risk_items", [])[:8]: st.write(f"- {item}")

    earn = build_earnings_basis(data.get("indicators"), data.get("profit"), code=code)
    model = detect_valuation_model(code, name, fin)
    config = get_valuation_config(model, fin)
    vr = calculate_valuation_scenarios(price=price, earnings_basis=earn, financials=fin, config=config)
    st.header("💎 四、当前估值")
    st.dataframe(pd.DataFrame([vr]), use_container_width=True, hide_index=True)

    hist = build_historical_pe(data.get("history"), data.get("indicators"), data.get("profit"), code=code)
    hs = calculate_historical_statistics(hist)
    st.header("📊 五、历史估值")
    st.write(f"历史PE分位：**{hs.get('percentile','暂无')}**")
    st.write(f"历史估值判断：**{get_historical_valuation_level(hs)}**")

    peer_codes = get_peer_candidates(code, name) or []
    peer_score = None
    if len(peer_codes) >= 2:
        rows=[]
        snap=load_peer_snapshots(tuple([code]+peer_codes[:5]))
        for pc in [code]+peer_codes[:5]:
            try:
                pdta=data if pc==code else snap.get(pc)
                if not pdta or pdta.get("indicators") is None or pdta["indicators"].empty: continue
                pfd=process_financial_indicators(pdta["indicators"],stock_code=pc)["annual"]
                pm=pdta.get("market") or {}; pp=pm.get("最新价") or get_latest_price(pdta.get("history"))
                pe=None if pp is None or pfd.get("eps") in {None,0} else pp/pfd["eps"]
                pbt=None if pp is None or pfd.get("bvps") in {None,0} else pp/pfd["bvps"]
                pname=pm.get("名称") or get_stock_name(pc) or pc
                rows.append({"代码":pc,"名称":pname,"价格":pp,"ROE":pfd.get("roe"),"营收增长率":pfd.get("revenue_growth"),"净利润增长率":pfd.get("profit_growth"),"PE":pe,"PB":pbt})
            except Exception: continue
        if len(rows)>=2:
            pdf=pd.DataFrame(rows); st.header("🏭 六、同行比较"); st.dataframe(pdf.round(2),use_container_width=True,hide_index=True)
            summ=build_peer_summary(pdf,exclude_code=code)
            if summ is not None and not summ.empty: st.caption("同行平均/中位数：已排除目标公司"); st.dataframe(summ,use_container_width=True,hide_index=True)
            comp=compare_target_with_average(pdf,code)
            if comp: st.dataframe(pd.DataFrame(comp),use_container_width=True,hide_index=True)
            pr=calculate_peer_score(pdf,code); peer_score=pr.get("score")

    gap=None if price is None or vr.get("normal") is None or vr.get("normal")<=0 else (vr["normal"]/price-1)*100
    score=calculate_investment_score(financial_score=fq["score"],peer_score=peer_score,valuation_gap=gap,risk_score=risk_score,historical_percentile=hs.get("percentile"))
    st.header("🏆 七、综合投资价值评分")
    a,b=st.columns(2); a.metric("投资价值评分",f"{score['score']}/100"); b.metric("投资评级",score["rating"])
    st.dataframe(pd.DataFrame({"分析维度":["财务质量","同行竞争力","当前估值","历史估值","风险控制"],"满分":[30,25,20,15,10],"实际得分":[score["financial_component"],score["peer_component"],score["valuation_component"],score["historical_component"],score["risk_component"]]}),use_container_width=True,hide_index=True)
    st.write(f"当前估值判断：**{score['valuation_level']}**"); st.write(f"历史估值判断：**{score['historical_level']}**"); st.write(f"风险判断：**{score['risk_level']}**")

    st.header("🎯 八、最终投资决策")
    decision=make_investment_decision(investment_score=score["score"],valuation_level=score["valuation_level"],historical_level=score["historical_level"],risk_level=score["risk_level"])
    a,b,c=st.columns(3); a.metric("投资决策",decision["decision"]); b.metric("建议操作",decision["action"]); c.metric("建议仓位",decision["position"]); st.info("💡 决策理由："+decision["reason"])

    record_research_snapshot(code=code,name=name,price=price,score=score.get("score"),rating=score.get("rating"),decision=decision.get("decision"),action=decision.get("action"),position=decision.get("position"),normal_value=vr.get("normal"),safety_margin=gap,valuation_level=score.get("valuation_level"),historical_level=score.get("historical_level"),risk_level=score.get("risk_level"))
    account=current_account()
    if account:
        try:
            save_research_snapshot(account.get("user_id", ""), {"code":code,"name":name,"score":score.get("score"),"decision":decision.get("decision"),"price":price,"normal_value":vr.get("normal"),"safety_margin":gap})
        except Exception:
            pass

    st.markdown(f"### 🎯 {name} · 核心研究结论")
    st.success(f"{decision['decision']}｜{decision['action']}｜建议仓位：{decision['position']}")
    a,b,c,d=st.columns(4); a.metric("综合评分",f"{score['score']}/100"); b.metric("中性合理价","暂无" if vr.get("normal") is None else f"{vr['normal']:.2f} 元"); c.metric("当前价格","暂无" if price is None else f"{price:.2f} 元"); d.metric("安全边际","暂无" if gap is None else f"{gap:+.1f}%")

    st.header("🏁 九、最终投资结论")
    if score["score"]>=85: conclusion="🟢 公司质量与估值较匹配，值得重点研究。"
    elif score["score"]>=75: conclusion="🟢 公司质量较好，值得长期跟踪。"
    elif score["score"]>=65: conclusion="🟡 公司具备一定价值，建议等待更好的安全边际。"
    elif score["score"]>=50: conclusion="🟠 当前投资吸引力一般，建议进一步观察。"
    else: conclusion="🔴 当前风险收益比较弱，暂不适合作为长期核心资产。"
    st.info(conclusion)

    st.markdown("---")
    st.subheader("⭐ 我的股票池")
    render_watchlist_dashboard()

# Pro 用户已登录且股票池存在时，研究页面下方提供轻量跟踪。
render_watchlist_tracking()

st.header("🛠️ 系统诊断")
st.caption("核心研究引擎保持独立；股票池跟踪属于商业层，不参与核心估值计算。")
