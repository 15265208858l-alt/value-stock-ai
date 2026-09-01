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

st.set_page_config(page_title="A股价值研投 | ValueStock AI", page_icon="📈", layout="wide")

st.markdown("""
<style>
:root{--vs-ink:#172033;--vs-muted:#6b778c;--vs-gold:#b8872d;--vs-gold2:#d4a94d;--vs-blue:#2563a8;--vs-bg:#f6f8fb;--vs-line:#e6eaf0}
.block-container{max-width:1180px;padding-top:1.2rem;padding-bottom:3rem}
.vs-brand{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 16px;padding:14px 16px;border:1px solid var(--vs-line);border-radius:18px;background:linear-gradient(135deg,#fffdf8,#f8fafc);box-shadow:0 5px 20px rgba(20,35,59,.05)}
.vs-brand-main{font-size:1.15rem;font-weight:900;color:var(--vs-ink);letter-spacing:.02em}.vs-brand-sub{font-size:.74rem;color:var(--vs-muted);margin-top:3px}.vs-brand-pill{white-space:nowrap;border-radius:999px;padding:6px 11px;background:#f5ead4;color:#7c5b20;font-size:.72rem;font-weight:800}
.vs-search-title{font-size:1.55rem;font-weight:900;color:var(--vs-ink);letter-spacing:.01em}.vs-search-sub{font-size:.92rem;color:var(--vs-muted);margin:4px 0 4px}.vs-search-tip{font-size:.78rem;color:#7b8798;margin-bottom:12px}
.vs-hero{padding:18px 18px 16px;border-radius:18px;background:linear-gradient(135deg,#eef5ff 0%,#fbfcfe 65%);border:1px solid #dce8f7;margin:10px 0 14px}.vs-hero-title{font-size:1.08rem;font-weight:900;color:#173b67}.vs-hero-text{font-size:.82rem;color:#53657a;line-height:1.65;margin-top:6px}
.vs-feature-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0}.vs-feature{padding:12px;border:1px solid var(--vs-line);border-radius:14px;background:#fff}.vs-feature b{display:block;color:var(--vs-ink);font-size:.84rem;margin-bottom:4px}.vs-feature span{font-size:.72rem;color:var(--vs-muted);line-height:1.45}
.vs-plan{border:1px solid #e6dfd0;border-radius:16px;padding:13px 14px;background:linear-gradient(135deg,#fffaf0,#fff);margin-top:12px}.vs-plan-title{font-weight:900;color:#7a5b22;font-size:.88rem}.vs-plan-text{font-size:.75rem;color:#69778a;line-height:1.5;margin-top:4px}
.vs-result{border:1px solid #e5e9ef;border-radius:18px;padding:15px 16px;background:#fff;box-shadow:0 7px 24px rgba(20,35,59,.06);margin:12px 0 18px}.vs-result-title{font-size:1rem;font-weight:900;color:var(--vs-ink);margin-bottom:9px}.vs-result-main{font-size:1.12rem;font-weight:900;color:#173b67}.vs-result-sub{font-size:.76rem;color:#66758a;margin-top:5px}.vs-result-good{border-left:5px solid #4b9b68}.vs-result-mid{border-left:5px solid var(--vs-gold)}.vs-result-bad{border-left:5px solid #c45a5a}
.vs-explain{background:#f7f9fb;border-radius:14px;padding:12px 14px;color:#506176;font-size:.86rem;margin-top:10px}.vs-company{font-size:1.35rem;font-weight:900;color:#14233b}.vs-badge{border-radius:999px;padding:5px 10px;background:#f4ead7;color:#7d5a16;font-weight:800}
[data-testid="stMetric"]{border:1px solid #edf0f4;border-radius:14px;background:#fff;padding:10px 11px;box-shadow:0 2px 10px rgba(20,35,59,.025)}
[data-testid="stMetricLabel"]{color:#68768a}
button[kind="primary"]{background:linear-gradient(135deg,var(--vs-gold2),var(--vs-gold))!important;border:0!important;color:#fff!important;font-weight:900!important;box-shadow:0 6px 16px rgba(184,135,45,.22)!important}
.stTextInput input{border-radius:12px!important;border:1px solid #dfe5ec!important}
@media(max-width:768px){
 .block-container{padding:.45rem .65rem 2rem!important}
 .vs-brand{padding:11px 12px;border-radius:14px;margin-bottom:12px}.vs-brand-main{font-size:1rem}.vs-brand-pill{font-size:.66rem;padding:5px 8px}
 .vs-search-title{font-size:1.32rem}.vs-search-sub{font-size:.84rem}.vs-search-tip{font-size:.72rem}
 .vs-hero{padding:14px;border-radius:15px}.vs-hero-title{font-size:.98rem}.vs-hero-text{font-size:.76rem}
 .vs-feature-grid{grid-template-columns:repeat(2,1fr);gap:8px}.vs-feature{padding:10px}.vs-feature b{font-size:.77rem}.vs-feature span{font-size:.67rem}
 .vs-result{padding:12px 13px;border-radius:15px}.vs-result-main{font-size:1rem}.vs-result-sub{font-size:.7rem}
 h1{font-size:1.42rem!important} h2{font-size:1.08rem!important} h3{font-size:.98rem!important}
 [data-testid="stMetric"]{padding:8px 9px!important;border-radius:12px!important}
 [data-testid="stMetricLabel"]{font-size:.68rem!important}
 [data-testid="stMetricValue"]{font-size:1.08rem!important}
 button[kind="primary"]{min-height:46px!important}
 .stTextInput input{font-size:16px!important}
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="vs-brand"><div><div class="vs-brand-main">📈 A股价值研投</div><div class="vs-brand-sub">ValueStock AI · 长期价值投资研究平台</div></div><div class="vs-brand-pill">长期价值 · 安全边际</div></div>', unsafe_allow_html=True)
st.markdown('<div class="vs-search-title">🔎 研究一家A股公司</div><div class="vs-search-sub">输入股票代码，快速查看企业质量、估值、安全边际与投资决策。</div><div class="vs-search-tip">📱 手机端优化：结论优先、关键指标卡片化、详细数据向下展开。</div>', unsafe_allow_html=True)
code_input=st.text_input("A股股票代码",placeholder="例如：000333",label_visibility="collapsed")
peer_input=st.text_input("同行股票代码",placeholder="同行可选填，例如：000651,600690",label_visibility="collapsed")
run=st.button("🔍 开始价值研究",type="primary",use_container_width=True)
if not run:
    st.markdown('<div class="vs-hero"><div class="vs-hero-title">🧠 一套面向长期价值投资的A股研究框架</div><div class="vs-hero-text">不追热点，不靠单一指标。系统围绕企业质量、现金流、正常化EPS、行业自适应估值、历史估值、同行比较与安全边际，形成可复核的研究结论。</div></div><div class="vs-feature-grid"><div class="vs-feature"><b>📊 企业质量</b><span>ROE、成长、负债与5年财务质量</span></div><div class="vs-feature"><b>💰 AI估值</b><span>PE/PB、正常化EPS与情景估值</span></div><div class="vs-feature"><b>🛡️ 风险排查</b><span>现金流、应收、存货等核心风险</span></div><div class="vs-feature"><b>🎯 投资决策</b><span>评分、安全边际与建议仓位</span></div></div><div class="vs-plan"><div class="vs-plan-title">⭐ 专业会员功能正在规划</div><div class="vs-plan-text">后续将提供更深度的历史数据、重点股票跟踪、估值提醒、研究报告与个人股票池。当前版本先把核心研究引擎和移动端体验做到稳定可靠。</div></div>',unsafe_allow_html=True)
    st.stop()
code=clean_stock_code(code_input)
if not code:
    st.error("❌ 请输入6位数字股票代码"); st.stop()

# 预留顶部结论位：所有计算完成后回填，手机用户无需滚到底部才能看到核心结论。
result_slot=st.empty()

# 性能核心：五类数据并行获取；去掉旧版多次长重试和全市场扫描。
with st.spinner("⚡ 正在快速获取A股核心数据……"):
    data=load_stock_data_fast(code)
if not data:
    st.error("❌ 股票数据加载失败，请稍后重试"); st.stop()

st.header("📡 一、数据中心")
dc=check_data_completeness(data)
a,b,c=st.columns(3); a.metric("数据完整度",f"{dc['score']}%"); b.metric("已获取模块",f"{dc['available']}/{dc['total']}"); c.metric("数据质量",dc["level"])

st.header("📌 二、目标公司行情")
m,h=data.get("market"),data.get("history"); name=code
price=chg=dyn_pe=None
if m:
    name=m.get("名称",code); price=m.get("最新价"); chg=m.get("涨跌幅"); dyn_pe=m.get("市盈率-动态")
if price is None: price=get_latest_price(h)
a,b,c,d=st.columns(4)
a.metric("股票名称",name); b.metric("当前价格","暂无" if price is None else f"{price:.2f} 元")
c.metric("涨跌幅","暂无" if chg is None else f"{chg:.2f}%"); d.metric("动态PE","暂无" if dyn_pe is None else f"{dyn_pe:.2f}")
st.success("✅ 历史行情获取成功" if h is not None else "⚠️ 历史行情暂时无法获取")

st.header("📊 三、财务分析")
ind=data.get("indicators")
fd={"latest":{},"annual":{},"trend":pd.DataFrame()}
if ind is not None and not ind.empty:
    try:
        fd=process_financial_indicators(ind,stock_code=code,profit_report=data.get("profit")) or fd
    except Exception:
        st.warning("⚠️ 财务指标解析异常，已启用安全降级，后续估值仍会继续。")
else:
    st.warning("⚠️ 财务指标暂不可用，后续模块将使用可获得数据继续。")
latest,annual,trend=fd.get("latest") or {},fd.get("annual") or {},fd.get("trend")
annual_roe=annual.get("roe"); annual_eps=annual.get("eps"); annual_bvps=annual.get("bvps"); annual_debt=annual.get("debt")
a,b,c,d=st.columns(4)
a.metric("最新ROE","暂无" if latest.get("roe") is None else f"{latest['roe']:.2f}%")
b.metric("营收增长","暂无" if latest.get("revenue_growth") is None else f"{latest['revenue_growth']:.2f}%")
c.metric("净利润增长","暂无" if latest.get("profit_growth") is None else f"{latest['profit_growth']:.2f}%")
d.metric("资产负债率","暂无" if latest.get("debt") is None else f"{latest['debt']:.2f}%")
a,b,c,d=st.columns(4)
a.metric("年度ROE","暂无" if annual_roe is None else f"{annual_roe:.2f}%")
b.metric("年度EPS","暂无" if annual_eps is None else f"{annual_eps:.2f} 元")
c.metric("年度BPS","暂无" if annual_bvps is None else f"{annual_bvps:.2f} 元")
d.metric("年度负债率","暂无" if annual_debt is None else f"{annual_debt:.2f}%")
if not latest and not annual: st.caption("ℹ️ 财务指标暂无有效数据，本次研究将以其他可用模块为主。")

def sf(v):
    try:
        if v is None or str(v).strip() in {"","--","None","nan","NaN"}: return None
        return float(str(v).replace(",","").replace("%",""))
    except Exception: return None

def col(df,names):
    if df is None or getattr(df,"empty",True): return None
    return next((x for x in names if x in df.columns),None)

def lastv(df,names):
    c=col(df,names)
    return None if c is None else sf(df.iloc[0][c])

def money(v): return "暂无" if v is None else f"{v/1e8:.2f} 亿元"

def report_values(data):
    return {"revenue":lastv(data.get("profit"),["营业总收入","营业收入","一、营业总收入"]),"net_profit":lastv(data.get("profit"),["归属于母公司所有者的净利润","归属于母公司股东的净利润","净利润","五、净利润"]),"receivable":lastv(data.get("balance"),["应收账款","应收款项"]),"inventory":lastv(data.get("balance"),["存货"]),"ocf":lastv(data.get("cashflow"),["经营活动产生的现金流量净额","经营活动现金流量净额"])}

st.header("💰 四、三大报表")
rv=report_values(data)
a,b,c,d,e=st.columns(5)
a.metric("营业收入",money(rv["revenue"])); b.metric("净利润",money(rv["net_profit"])); c.metric("经营现金流",money(rv["ocf"])); d.metric("应收账款",money(rv["receivable"])); e.metric("存货",money(rv["inventory"]))

st.header("🚨 五、财务排雷")
risk=analyze_financial_risk(rv["ocf"],rv["net_profit"],rv["receivable"],rv["revenue"],rv["inventory"],annual_roe,annual_debt)
risk_score=risk.get("score",5); st.metric("财务风险评分",f"{risk_score}/10")
for x in risk.get("risk_items",[]): st.warning(f"⚠️ {x}")
if not risk.get("risk_items"): st.success("✅ 暂未发现明显财务风险")
cash_ratio=None if rv["ocf"] is None or rv["net_profit"] in {None,0} else rv["ocf"]/rv["net_profit"]

st.header("📈 六、5年财务质量")
fq=calculate_financial_quality(trend,cash_ratio)
a,b=st.columns(2); a.metric("财务质量评分",f"{fq['score']}/100"); b.metric("财务质量评级",fq["rating"])
if trend is not None and not trend.empty: st.dataframe(trend,use_container_width=True,hide_index=True)

st.header("💰 七、当前价值估值")
override=st.selectbox("🧠 估值模型（默认自动识别，可手动调整）",["自动识别","普通成长/制造","成长科技","银行","保险","券商","周期"],index=0)
model=detect_valuation_model(stock_code=code,override=override); cfg=dict(get_valuation_config(model,annual_roe=annual_roe))
try:
    earn=build_earnings_basis(indicators=ind,annual_eps=annual_eps,operating_cashflow_ratio=cash_ratio,profit_growth=latest.get("profit_growth"),stock_code=code) or {}
except Exception:
    earn={}
normalized_eps=earn.get("normalized_eps"); valuation_eps=normalized_eps or annual_eps
annual_pe=None if price is None or annual_eps is None or annual_eps<=0 else price/annual_eps
hist=build_historical_pe(h,trend,max_years=10); hs=calculate_historical_statistics(hist,annual_pe)
if model=="growth_tech":
    try:
        gq=calculate_growth_quality(revenue_growth=latest.get("revenue_growth"),profit_growth=latest.get("profit_growth"),roe=latest.get("roe") if latest.get("roe") is not None else annual_roe,cashflow_ratio=cash_ratio,ttm_eps=earn.get("ttm_eps"),annual_eps=annual_eps,historical_percentile=hs.get("percentile"))
        dynamic_pe=get_dynamic_growth_pe(gq["score"],historical_percentile=hs.get("percentile"),cashflow_ratio=cash_ratio)
        cfg["conservative_pe"]=dynamic_pe["conservative_pe"]; cfg["normal_pe"]=dynamic_pe["normal_pe"]; cfg["optimistic_pe"]=dynamic_pe["optimistic_pe"]
    except Exception:
        gq=None
    st.info(f"🧠 当前估值模型：{cfg['name']}｜动态成长PE + PB")
else:
    gq=None; st.info(f"🧠 当前估值模型：{cfg['name']}｜{cfg['method']}")
a,b,c,d=st.columns(4)
a.metric("年度EPS","暂无" if annual_eps is None else f"{annual_eps:.2f}"); b.metric("TTM EPS","暂无" if earn.get("ttm_eps") is None else f"{earn['ttm_eps']:.2f}"); c.metric("正常化EPS（估值用）","暂无" if normalized_eps is None else f"{normalized_eps:.2f}"); d.metric("盈利兑现评分","暂无" if earn.get("realization_score") is None else f"{earn['realization_score']}/100")
real_coeff=earn.get("realization_coefficient"); st.caption(f"盈利兑现系数：{'暂无' if real_coeff is None else f'{real_coeff:.3f}'}｜等级：{earn.get('realization_level','低')}｜{earn.get('note','数据不足')}")
if gq is not None:
    a,b,c=st.columns(3); a.metric("成长质量",f"{gq['score']}/100"); b.metric("成长质量等级",gq["level"]); c.metric("动态PE区间",f"{cfg['conservative_pe']:.1f}～{cfg['optimistic_pe']:.1f}倍")
    st.caption(f"成长质量拆解：营收 {gq['revenue_points']:+.0f}｜利润 {gq['profit_points']:+.0f}｜ROE {gq['roe_points']:+.0f}｜现金流 {gq['cash_points']:+.0f}｜盈利动能 {gq['momentum_points']:+.0f}｜历史估值修正 {gq['history_penalty']:+.0f}")
valuation_pe=None if price is None or valuation_eps is None or valuation_eps<=0 else price/valuation_eps
pb=None if price is None or annual_bvps is None or annual_bvps<=0 else price/annual_bvps
vr=calculate_valuation_scenarios(eps=valuation_eps,bvps=annual_bvps,conservative_pe=cfg["conservative_pe"],normal_pe=cfg["normal_pe"],optimistic_pe=cfg["optimistic_pe"],conservative_pb=cfg["conservative_pb"],normal_pb=cfg["normal_pb"],optimistic_pb=cfg["optimistic_pb"],pe_weight=cfg["pe_weight"],pb_weight=cfg["pb_weight"])
a,b,c,d,e=st.columns(5)
a.metric("当前PE（年度）","暂无" if annual_pe is None else f"{annual_pe:.2f}"); b.metric("当前PE（估值口径）","暂无" if valuation_pe is None else f"{valuation_pe:.2f}"); c.metric("当前PB","暂无" if pb is None else f"{pb:.2f}"); d.metric("中性合理价","暂无" if vr["normal"] is None else f"{vr['normal']:.2f} 元"); e.metric("建仓参考价","暂无" if vr["entry_price"] is None else f"{vr['entry_price']:.2f} 元")
st.write(f"保守价值：{vr['conservative']:.2f} 元 ｜ 乐观价值：{vr['optimistic']:.2f} 元 ｜ 重仓参考价：{vr['heavy_price']:.2f} 元")
if vr.get("pe_values") or vr.get("pb_values"):
    st.caption("🔎 估值路径拆解")
    st.dataframe(pd.DataFrame({"情景":["保守","中性","乐观"],"PE路径价值":[vr.get("pe_values",{}).get("conservative"),vr.get("pe_values",{}).get("normal"),vr.get("pe_values",{}).get("optimistic")],"PB路径价值":[vr.get("pb_values",{}).get("conservative"),vr.get("pb_values",{}).get("normal"),vr.get("pb_values",{}).get("optimistic")],"综合价值":[vr.get("conservative"),vr.get("normal"),vr.get("optimistic")]}).round(2),use_container_width=True,hide_index=True)

historical_eps_cagr=calculate_eps_cagr(trend,years=3)
if historical_eps_cagr is not None and valuation_eps is not None and cfg.get("normal_pe") is not None:
    st.subheader("🧭 7.5 历史盈利情景估值"); st.caption("这不是预测价格，而是用过去已经实现的EPS增长速度做敏感性分析；PE固定采用当前模型的中性PE。")
    rows=build_growth_sensitivity(base_eps=valuation_eps,normal_pe=cfg["normal_pe"],years=3,historical_cagr=historical_eps_cagr)
    if rows:
        st.metric("近3年历史EPS CAGR",f"{historical_eps_cagr*100:+.1f}%")
        scenario_df=pd.DataFrame(rows); scenario_df["年化EPS增长假设"]=scenario_df["年化EPS增长假设"]*100
        st.dataframe(scenario_df.round(2),use_container_width=True,hide_index=True)
        st.caption("⚠️ 保守/历史趋势/乐观仅用于压力测试，不代表公司未来一定达到该增长率。")
else:
    st.caption("🧭 历史盈利情景估值：历史EPS样本不足，暂不外推。")

st.header("📊 八、历史PE估值")
hist_level=get_historical_valuation_level(hs.get("percentile"))
if hist is not None and not hist.empty:
    st.dataframe(hist.round(2),use_container_width=True,hide_index=True)
    a,b,c=st.columns(3); a.metric("历史最低PE","暂无" if hs.get("min") is None else f"{hs['min']:.2f}"); b.metric("历史中位PE","暂无" if hs.get("median") is None else f"{hs['median']:.2f}"); c.metric("历史最高PE","暂无" if hs.get("max") is None else f"{hs['max']:.2f}")
    a,b,c=st.columns(3); a.metric("历史25%分位","暂无" if hs.get("q25") is None else f"{hs['q25']:.2f}"); b.metric("历史75%分位","暂无" if hs.get("q75") is None else f"{hs['q75']:.2f}"); c.metric("当前PE历史分位","暂无" if hs.get("percentile") is None else f"{hs['percentile']:.1f}%")
    st.write(f"**历史估值区域：{hist_level}**")
else: st.warning("⚠️ 历史PE数据不足")

st.header("🏭 九、同行业比较")
auto=get_peer_candidates(code,max_peers=5); peer_codes=auto.get("peers",[]) if auto else []
if not peer_codes and peer_input:
    peer_codes=[clean_stock_code(x) for x in peer_input.split(",") if clean_stock_code(x) and clean_stock_code(x)!=code]
if peer_codes:
    st.caption(f"自动行业：{auto.get('industry') if auto else '未识别'}｜同行：{', '.join([f'{pc} {get_stock_name(pc) or pc}' for pc in peer_codes[:5]])}")
else:
    st.warning("⚠️ 自动同行识别失败，可手动输入2～5只同行股票")
peer_score=None
if len(peer_codes)>=2:
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
        pdf=pd.DataFrame(rows); st.dataframe(pdf.round(2),use_container_width=True,hide_index=True)
        summ=build_peer_summary(pdf,exclude_code=code)
        if summ is not None and not summ.empty: st.caption("同行平均/中位数：已排除目标公司"); st.dataframe(summ,use_container_width=True,hide_index=True)
        comp=compare_target_with_average(pdf,code)
        if comp: st.dataframe(pd.DataFrame(comp),use_container_width=True,hide_index=True)
        pr=calculate_peer_score(pdf,code); peer_score=pr.get("score"); rel=pr.get("relative_valuation") or {}
        st.metric("同行竞争力","暂无" if peer_score is None else f"{peer_score}/100")
        if rel.get("available"):
            ra,rb,rc=st.columns(3); ra.metric("同行PE中位数","暂无" if rel.get("peer_median_pe") is None else f"{rel['peer_median_pe']:.2f}倍"); rb.metric("同行PB中位数","暂无" if rel.get("peer_median_pb") is None else f"{rel['peer_median_pb']:.2f}倍"); rc.metric("相对估值判断",rel.get("level","数据不足"))
            st.caption(f"目标PE/同行中位PE：{rel.get('pe_ratio','暂无')}｜目标PB/同行中位PB：{rel.get('pb_ratio','暂无')}")
    else:
        st.warning("⚠️ 同行数据不足，已跳过同行评分")

st.header("🏆 十、综合投资价值评分")
gap=None if price is None or vr["normal"] is None or vr["normal"]<=0 else (vr["normal"]/price-1)*100
score=calculate_investment_score(financial_score=fq["score"],peer_score=peer_score,valuation_gap=gap,risk_score=risk_score,historical_percentile=hs.get("percentile"))
a,b=st.columns(2); a.metric("投资价值评分",f"{score['score']}/100"); b.metric("投资评级",score["rating"])
st.dataframe(pd.DataFrame({"分析维度":["财务质量","同行竞争力","当前估值","历史估值","风险控制"],"满分":[30,25,20,15,10],"实际得分":[score["financial_component"],score["peer_component"],score["valuation_component"],score["historical_component"],score["risk_component"]]}),use_container_width=True,hide_index=True)
st.write(f"当前估值判断：**{score['valuation_level']}**"); st.write(f"历史估值判断：**{score['historical_level']}**"); st.write(f"风险判断：**{score['risk_level']}**")
if score.get("relative_valuation_available"): st.write(f"同行相对估值：**{score['relative_valuation_level']}**｜同行PE中位数 {score.get('peer_median_pe','暂无')}倍｜目标PE/同行中位 {score.get('relative_pe_ratio','暂无')}")

st.header("🎯 十一、最终投资决策")
decision=make_investment_decision(investment_score=score["score"],valuation_level=score["valuation_level"],historical_level=score["historical_level"],risk_level=score["risk_level"])
a,b,c=st.columns(3); a.metric("投资决策",decision["decision"]); b.metric("建议操作",decision["action"]); c.metric("建议仓位",decision["position"]); st.info("💡 决策理由："+decision["reason"])
st.markdown('<div class="vs-explain"><b>🎯 核心研究结论</b></div>',unsafe_allow_html=True)
a,b,c,d=st.columns(4); a.metric("综合评分",f"{score['score']}/100"); b.metric("中性合理价","暂无" if vr.get("normal") is None else f"{vr['normal']:.2f} 元"); c.metric("当前价格","暂无" if price is None else f"{price:.2f} 元"); d.metric("安全边际","暂无" if gap is None else f"{gap:+.1f}%")
st.markdown(f'<div class="vs-company">{name} <span class="vs-badge">{score["rating"]}</span></div><div class="vs-explain">最终建议：<b>{decision["decision"]}</b>｜操作：{decision["action"]}｜仓位：{decision["position"]}<br>估值：{score["valuation_level"]}｜历史估值：{score["historical_level"]}｜风险：{score["risk_level"]}</div>',unsafe_allow_html=True)

# 回填顶部核心结论卡：使用占位容器可在计算完成后把结论放到页面最上方。
result_class="vs-result-good" if score["score"]>=75 else "vs-result-mid" if score["score"]>=60 else "vs-result-bad"
result_slot.markdown(f'<div class="vs-result {result_class}"><div class="vs-result-title">🎯 {name} · 核心研究结论</div><div class="vs-result-main">{decision["decision"]} · {decision["action"]}</div><div class="vs-result-sub">综合评分 {score["score"]}/100　｜　当前价格 {"暂无" if price is None else f"{price:.2f} 元"}　｜　中性合理价 {"暂无" if vr.get("normal") is None else f"{vr["normal"]:.2f} 元"}　｜　安全边际 {"暂无" if gap is None else f"{gap:+.1f}%"}</div><div class="vs-result-sub">估值：{score["valuation_level"]}　｜　历史估值：{score["historical_level"]}　｜　风险：{score["risk_level"]}　｜　建议仓位：{decision["position"]}</div></div>',unsafe_allow_html=True)

st.header("🏆 十二、最终投资结论")
if score["score"]>=85: conclusion="🟢 公司质量与估值较匹配，值得重点研究。"
elif score["score"]>=75: conclusion="🟢 公司质量较好，值得长期跟踪。"
elif score["score"]>=65: conclusion="🟡 公司具备一定价值，建议等待更好的安全边际。"
elif score["score"]>=50: conclusion="🟠 当前投资吸引力一般，建议进一步观察。"
else: conclusion="🔴 当前风险收益比较弱，暂不适合作为长期核心资产。"
st.info(conclusion)
if risk.get("risk_items"):
    st.subheader("⚠️ 核心风险")
    for x in risk["risk_items"]: st.write(f"- {x}")

st.header("🛠️ 十三、系统诊断")
st.dataframe(pd.DataFrame({"模块":["fast_data.py","financial.py","risk.py","valuation.py","adaptive_valuation.py","earnings_basis.py","growth_quality.py","historical_valuation.py","peer_compare.py","industry.py","investment_score.py","investment_decision.py"],"状态":["✅","✅","✅","✅","✅","✅" if earn.get("valuation_eps") is not None else "⏳","✅" if gq is not None else "⏳","✅" if hist is not None and not hist.empty else "⏳","✅" if peer_score is not None else "⏳","✅" if peer_codes else "⏳","✅","✅"]}),use_container_width=True,hide_index=True)
st.divider(); st.caption("A股价值研投｜ValueStock AI：正常化EPS + 盈利兑现 + 成长质量 + 历史估值 + 同行比较 + 安全边际 + 综合投资决策")
