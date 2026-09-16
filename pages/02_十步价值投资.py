import streamlit as st
import pandas as pd

from fast_data import clean_stock_code, load_stock_data_fast, get_latest_price
from financial import process_financial_indicators
from fcf_analysis import analyze_fcf_from_frames
from governance_analysis import analyze_governance
from risk import analyze_financial_risk
from earnings_basis import build_earnings_basis
from adaptive_valuation import detect_valuation_model, get_valuation_config
from valuation import calculate_valuation_scenarios
from industry import get_peer_candidates, get_stock_name

st.set_page_config(page_title="10步价值投资 | ValueStock AI", page_icon="🧭", layout="wide")
st.title("🧭 10步长期价值投资分析")
st.caption("围绕行业、护城河、成长、ROE、现金流、资产负债、营运资本、减值风险、治理与估值安全边际进行结构化研究。")


def num(v):
    try:
        if v is None or str(v).strip() in {"", "--", "None", "nan", "NaN"}:
            return None
        return float(str(v).replace(",", "").replace("%", ""))
    except Exception:
        return None


def find_col(df, names):
    if df is None or getattr(df, "empty", True):
        return None
    return next((x for x in names if x in df.columns), None)


def latest(df, names):
    c = find_col(df, names)
    return None if c is None else num(df.iloc[0][c])


def money(v):
    return "数据不足" if v is None else f"{v / 1e8:.2f}亿元"


def status(condition, good="较好", bad="需关注", missing="数据不足"):
    if condition is None:
        return missing
    return good if condition else bad


code_input = st.text_input("输入A股股票代码", placeholder="例如：000333")
run = st.button("🚀 开始10步分析", type="primary", use_container_width=True)

if not run:
    st.info("输入股票代码后，系统会读取现有 ValueStock AI 数据链路并生成10步研究表。")
    st.stop()

code = clean_stock_code(code_input)
if not code:
    st.error("请输入6位A股股票代码")
    st.stop()

with st.spinner("正在加载公司数据……"):
    data = load_stock_data_fast(code)

if not data:
    st.error("股票数据加载失败，请稍后重试")
    st.stop()

market = data.get("market") or {}
name = market.get("名称") or get_stock_name(code) or code
price = num(market.get("最新价"))
if price is None:
    price = get_latest_price(data.get("history"))

ind = data.get("indicators")
profit = data.get("profit")
balance = data.get("balance")
cashflow = data.get("cashflow")

fd = {"latest": {}, "annual": {}, "trend": pd.DataFrame()}
if ind is not None and not ind.empty:
    try:
        fd = process_financial_indicators(ind, stock_code=code, profit_report=profit) or fd
    except Exception:
        fd = {"latest": {}, "annual": {}, "trend": pd.DataFrame()}

latest_m = fd.get("latest") or {}
annual = fd.get("annual") or {}
trend = fd.get("trend")

roe = latest_m.get("roe") if latest_m.get("roe") is not None else annual.get("roe")
revenue_growth = latest_m.get("revenue_growth")
profit_growth = latest_m.get("profit_growth")
debt = latest_m.get("debt") if latest_m.get("debt") is not None else annual.get("debt")
eps = annual.get("eps")
bvps = annual.get("bvps")

revenue = latest(profit, ["营业总收入", "营业收入", "一、营业总收入"])
net_profit = latest(profit, ["归属于母公司所有者的净利润", "归属于母公司股东的净利润", "净利润", "五、净利润"])
receivable = latest(balance, ["应收账款", "应收款项"])
inventory = latest(balance, ["存货"])
ocf = latest(cashflow, ["经营活动产生的现金流量净额", "经营活动现金流量净额"])
goodwill = latest(balance, ["商誉"])

fcf = analyze_fcf_from_frames(profit_report=profit, cashflow=cashflow) or {}
try:
    cash_ratio = None if ocf is None or net_profit in {None, 0} else ocf / net_profit
except Exception:
    cash_ratio = None

governance = analyze_governance(balance=balance, shareholders=data.get("shareholders"), related_party=data.get("related_party")) or {}
risk = analyze_financial_risk(operating_cashflow=ocf, net_profit=net_profit, receivable=receivable, revenue=revenue, inventory=inventory, roe=roe, debt_ratio=debt) or {}

try:
    earn = build_earnings_basis(indicators=ind, annual_eps=eps, operating_cashflow_ratio=cash_ratio, profit_growth=profit_growth, stock_code=code) or {}
except Exception:
    earn = {}

peer = get_peer_candidates(code, max_peers=5) or {}
peer_codes = peer.get("peers", [])
peer_names = [get_stock_name(x) or x for x in peer_codes[:5]]

model = detect_valuation_model(stock_code=code, override="自动识别")
cfg = get_valuation_config(model, annual_roe=annual.get("roe"))
valuation_eps = earn.get("normalized_eps") or eps
vr = calculate_valuation_scenarios(
    eps=valuation_eps,
    bvps=bvps,
    conservative_pe=cfg["conservative_pe"],
    normal_pe=cfg["normal_pe"],
    optimistic_pe=cfg["optimistic_pe"],
    conservative_pb=cfg["conservative_pb"],
    normal_pb=cfg["normal_pb"],
    optimistic_pb=cfg["optimistic_pb"],
    pe_weight=cfg["pe_weight"],
    pb_weight=cfg["pb_weight"],
    current_price=price,
    risk_level=risk.get("level"),
    data_confidence="高",
)

# 10步研究对象
steps = [
    {
        "步骤": "01 行业与成长空间",
        "结论": status(bool(peer_codes), f"已识别行业，同行：{', '.join(peer_names)}", "行业/同行识别需要复核"),
        "证据": f"行业：{peer.get('industry') or '数据不足'}；营收增长：{('%.1f%%' % revenue_growth) if revenue_growth is not None else '数据不足'}；利润增长：{('%.1f%%' % profit_growth) if profit_growth is not None else '数据不足'}",
        "风险": "行业空间不能仅由近年增速代表，仍需结合竞争格局、渗透率与周期位置人工验证。",
    },
    {
        "步骤": "02 企业护城河",
        "结论": "初步判断，需人工验证",
        "证据": f"ROE：{('%.1f%%' % roe) if roe is not None else '数据不足'}；同行：{len(peer_codes)}家；5年趋势样本：{0 if trend is None else len(trend)}期",
        "风险": "品牌、渠道、成本、技术、网络效应等真正护城河暂未完全结构化，系统不替你猜测。",
    },
    {
        "步骤": "03 长期营收与净利润成长",
        "结论": status(revenue_growth is not None and profit_growth is not None and revenue_growth >= 5 and profit_growth >= 5, "成长指标整体较好", "成长质量需要关注"),
        "证据": f"营收增长：{('%.1f%%' % revenue_growth) if revenue_growth is not None else '数据不足'}；净利润增长：{('%.1f%%' % profit_growth) if profit_growth is not None else '数据不足'}",
        "风险": "单年增长不等于长期增长，需要结合多年趋势与利润兑现验证。",
    },
    {
        "步骤": "04 ROE及盈利能力",
        "结论": status(roe is not None and roe >= 15, "盈利能力较强", "盈利能力一般/需观察"),
        "证据": f"ROE：{('%.1f%%' % roe) if roe is not None else '数据不足'}；年度EPS：{('%.2f元' % eps) if eps is not None else '数据不足'}",
        "风险": "必须继续区分经营效率驱动还是高杠杆驱动。",
    },
    {
        "步骤": "05 经营现金流与利润匹配",
        "结论": status(cash_ratio is not None and cash_ratio >= 0.8, "现金含量较好", "现金流与利润匹配度需要关注"),
        "证据": f"经营现金流：{money(ocf)}；净利润：{money(net_profit)}；OCF/净利润：{('%.2fx' % cash_ratio) if cash_ratio is not None else '数据不足'}；自由现金流：{money(fcf.get('fcf'))}",
        "风险": "经营现金流持续弱于利润，是长期价值投资的重要排雷点。",
    },
    {
        "步骤": "06 资产负债表与偿债能力",
        "结论": status(debt is not None and debt < 60, "负债水平可接受", "负债水平需要重点关注"),
        "证据": f"资产负债率：{('%.1f%%' % debt) if debt is not None else '数据不足'}",
        "风险": "不同产业合理负债率不同，金融、地产等行业不能直接套用制造业阈值。",
    },
    {
        "步骤": "07 应收账款与存货质量",
        "结论": "需结合收入规模动态观察",
        "证据": f"应收账款：{money(receivable)}；存货：{money(inventory)}；应收/营收：{('%.1f%%' % (receivable/revenue*100)) if receivable is not None and revenue else '数据不足'}",
        "风险": "应收、存货快速上升但收入与现金流没有同步改善时，需要警惕利润质量。",
    },
    {
        "步骤": "08 商誉、资本开支与潜在减值",
        "结论": "初步排查",
        "证据": f"商誉：{money(goodwill)}；资本开支/经营现金流：{('%.2fx' % fcf.get('capex_to_ocf')) if fcf.get('capex_to_ocf') is not None else '数据不足'}",
        "风险": "商誉减值、过度资本开支和低回报扩张可能吞噬自由现金流。",
    },
    {
        "步骤": "09 管理层与公司治理",
        "结论": governance.get("level", "数据不足"),
        "证据": f"治理数据：{'可分析' if governance.get('available') else '数据不足'}；治理风险分：{governance.get('score', 0)}/4",
        "风险": "关联交易、股东结构和资本运作等治理因素需要持续跟踪。",
    },
    {
        "步骤": "10 长期价值与估值安全边际",
        "结论": vr.get("valuation_status", "数据不足"),
        "证据": f"估值模型：{cfg.get('name', model)}；保守价值：{vr.get('conservative') if vr.get('conservative') is not None else '数据不足'}；中性价值：{vr.get('normal') if vr.get('normal') is not None else '数据不足'}；乐观价值：{vr.get('optimistic') if vr.get('optimistic') is not None else '数据不足'}；安全边际：{('%.1f%%' % (vr['safety_margin']*100)) if vr.get('safety_margin') is not None else '数据不足'}",
        "风险": "估值结果依赖盈利口径、PE/PB参数和行业模型，必须与历史估值及业务质量交叉验证。",
    },
]

st.subheader(f"🏢 {name}（{code}）")
a, b, c = st.columns(3)
a.metric("当前价格", "暂无" if price is None else f"{price:.2f}元")
b.metric("财务风险", risk.get("level", "数据不足"))
c.metric("估值模型", cfg.get("short_name", model))

st.dataframe(pd.DataFrame(steps), use_container_width=True, hide_index=True)

st.subheader("🎯 四档价格参考")
price_rows = pd.DataFrame({
    "价格区间": ["重仓参考价", "建仓参考价", "中性合理价", "高估参考价"],
    "数值": [vr.get("heavy_price"), vr.get("entry_price"), vr.get("normal"), vr.get("optimistic")],
    "说明": ["较大安全边际区域", "开始分批研究/建仓参考", "中性合理价值", "乐观情景附近，不等于目标价"],
})
price_rows["数值"] = price_rows["数值"].apply(lambda x: "暂无" if x is None else f"{x:.2f}元")
st.dataframe(price_rows, use_container_width=True, hide_index=True)

st.warning("⚠️ 本页面是研究辅助工具，不构成个性化投资建议。系统明确标记数据不足的环节，不用猜测填补缺失信息。")
