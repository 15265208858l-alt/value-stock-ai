import streamlit as st
import akshare as ak
import pandas as pd

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("A股长期价值投资分析 V6")
st.caption("利润质量 + 现金流 + 应收账款 + 存货排雷")

st.divider()


# =========================================================
# 1. 基础函数
# =========================================================

def get_market_code(stock_code):
    """根据股票代码判断市场"""

    if stock_code.startswith(("6", "68")):
        return "sh" + stock_code

    elif stock_code.startswith(("0", "3")):
        return "sz" + stock_code

    elif stock_code.startswith(("4", "8")):
        return "bj" + stock_code

    return stock_code


def get_history_data(stock_code):
    """获取腾讯历史行情"""

    market_code = get_market_code(stock_code)

    data = ak.stock_zh_a_hist_tx(
        symbol=market_code,
        start_date="20200101",
        end_date="20500101",
        adjust=""
    )

    if data is None or data.empty:
        return None

    return data


def get_financial_indicators(stock_code):
    """获取财务分析指标"""

    data = ak.stock_financial_analysis_indicator(
        symbol=stock_code
    )

    if data is None or data.empty:
        return None

    return data


def get_financial_report(stock_code, report_type):
    """获取新浪财务报表"""

    market_code = get_market_code(stock_code)

    data = ak.stock_financial_report_sina(
        stock=market_code,
        symbol=report_type
    )

    if data is None or data.empty:
        return None

    return data


def safe_float(value):
    """安全转换数字"""

    try:

        if value is None:
            return None

        text = str(value).strip()

        if text in ["", "--", "nan", "None", "NaN"]:
            return None

        text = text.replace(",", "")

        return float(text)

    except Exception:
        return None


def find_column(df, candidates):
    """寻找可能存在的字段"""

    if df is None:
        return None

    for col in candidates:

        if col in df.columns:
            return col

    return None


def safe_ratio(a, b):
    """安全计算比例"""

    if a is None or b is None:
        return None

    if b == 0:
        return None

    return a / b


# =========================================================
# 2. 输入股票代码
# =========================================================

stock_code = st.text_input(
    "请输入A股股票代码",
    placeholder="例如：600089、000333、601899"
)


if st.button(
    "开始财务排雷",
    type="primary"
):

    if not stock_code:

        st.warning("⚠️ 请先输入股票代码")

        st.stop()


    stock_code = stock_code.strip()


    if len(stock_code) != 6 or not stock_code.isdigit():

        st.error(
            "❌ 股票代码必须是6位数字，例如：600089"
        )

        st.stop()


    st.info(
        f"正在进行 {stock_code} 财务排雷，请稍候……"
    )


    # =====================================================
    # 3. 获取历史行情
    # =====================================================

    try:

        history = get_history_data(
            stock_code
        )

        if history is not None:

            latest_market = history.iloc[-1]

            st.success(
                "✅ A股历史行情获取成功"
            )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "最新收盘价",
                f"{float(latest_market['close']):.2f}"
            )

            c2.metric(
                "最高价",
                f"{float(latest_market['high']):.2f}"
            )

            c3.metric(
                "最低价",
                f"{float(latest_market['low']):.2f}"
            )

        else:

            st.warning(
                "⚠️ 没有获取到历史行情"
            )

    except Exception as e:

        st.error(
            "❌ 历史行情获取失败"
        )

        st.code(str(e))


    # =====================================================
    # 4. 获取财务指标
    # =====================================================

    try:

        indicators = get_financial_indicators(
            stock_code
        )

        if indicators is None:

            st.error(
                "❌ 财务指标获取失败"
            )

            st.stop()


        st.success(
            "✅ 财务指标获取成功"
        )


        latest_indicator = indicators.iloc[0]


        # -----------------------------
        # ROE
        # -----------------------------

        roe_col = find_column(
            indicators,
            [
                "加权净资产收益率(%)",
                "加权净资产收益率",
                "净资产收益率(%)",
                "净资产收益率"
            ]
        )


        # -----------------------------
        # 营收增长率
        # -----------------------------

        revenue_growth_col = find_column(
            indicators,
            [
                "主营业务收入增长率(%)",
                "主营业务收入增长率"
            ]
        )


        # -----------------------------
        # 净利润增长率
        # -----------------------------

        profit_growth_col = find_column(
            indicators,
            [
                "净利润增长率(%)",
                "净利润增长率"
            ]
        )


        # -----------------------------
        # 资产负债率
        # -----------------------------

        debt_col = find_column(
            indicators,
            [
                "资产负债率(%)",
                "资产负债率"
            ]
        )


        roe = (
            safe_float(
                latest_indicator[roe_col]
            )
            if roe_col
            else None
        )


        revenue_growth = (
            safe_float(
                latest_indicator[
                    revenue_growth_col
                ]
            )
            if revenue_growth_col
            else None
        )


        profit_growth = (
            safe_float(
                latest_indicator[
                    profit_growth_col
                ]
            )
            if profit_growth_col
            else None
        )


        debt_ratio = (
            safe_float(
                latest_indicator[
                    debt_col
                ]
            )
            if debt_col
            else None
        )


        # -----------------------------
        # 显示核心指标
        # -----------------------------

        st.subheader(
            "📊 当前核心指标"
        )


        a, b, c, d = st.columns(4)


        a.metric(
            "ROE",
            "暂无"
            if roe is None
            else f"{roe:.2f}%"
        )


        b.metric(
            "营收增长率",
            "暂无"
            if revenue_growth is None
            else f"{revenue_growth:.2f}%"
        )


        c.metric(
            "净利润增长率",
            "暂无"
            if profit_growth is None
            else f"{profit_growth:.2f}%"
        )


        d.metric(
            "资产负债率",
            "暂无"
            if debt_ratio is None
            else f"{debt_ratio:.2f}%"
        )


    except Exception as e:

        st.error(
            "❌ 财务指标分析失败"
        )

        st.code(
            str(e)
        )

        st.stop()


    # =====================================================
    # 5. 获取三张财务报表
    # =====================================================

    try:

        profit = get_financial_report(
            stock_code,
            "利润表"
        )


        balance = get_financial_report(
            stock_code,
            "资产负债表"
        )


        cashflow = get_financial_report(
            stock_code,
            "现金流量表"
        )


        st.success(
            "✅ 三张财务报表获取完成"
        )


    except Exception as e:

        st.error(
            "❌ 财务报表获取失败"
        )

        st.code(
            str(e)
        )

        st.stop()


    # =====================================================
    # 6. 原始财务报表
    # =====================================================

    with st.expander(
        "📋 查看原始财务报表"
    ):

        if profit is not None:

            st.write("### 利润表")

            st.dataframe(
                profit.head(15),
                use_container_width=True
            )


        if balance is not None:

            st.write("### 资产负债表")

            st.dataframe(
                balance.head(15),
                use_container_width=True
            )


        if cashflow is not None:

            st.write("### 现金流量表")

            st.dataframe(
                cashflow.head(15),
                use_container_width=True
            )


    # =====================================================
    # 7. 查找利润表关键字段
    # =====================================================

    st.divider()

    st.subheader(
        "🔎 财务排雷核心检查"
    )


    revenue_col = find_column(
        profit,
        [
            "营业总收入",
            "营业收入",
            "一、营业总收入"
        ]
    )


    net_profit_col = find_column(
        profit,
        [
            "净利润",
            "五、净利润"
        ]
    )


    # =====================================================
    # 8. 查找资产负债表关键字段
    # =====================================================

    receivable_col = find_column(
        balance,
        [
            "应收账款",
            "应收款项"
        ]
    )


    inventory_col = find_column(
        balance,
        [
            "存货"
        ]
    )


    # =====================================================
    # 9. 查找现金流量表关键字段
    # =====================================================

    operating_cash_col = find_column(
        cashflow,
        [
            "经营活动产生的现金流量净额",
            "经营活动现金流量净额"
        ]
    )


    # =====================================================
    # 10. 获取最近一期数据
    # =====================================================

    latest_revenue = None

    latest_profit = None

    latest_receivable = None

    latest_inventory = None

    latest_cashflow = None


    if revenue_col:

        latest_revenue = safe_float(
            profit.iloc[0][revenue_col]
        )


    if net_profit_col:

        latest_profit = safe_float(
            profit.iloc[0][net_profit_col]
        )


    if receivable_col:

        latest_receivable = safe_float(
            balance.iloc[0][receivable_col]
        )


    if inventory_col:

        latest_inventory = safe_float(
            balance.iloc[0][inventory_col]
        )


    if operating_cash_col:

        latest_cashflow = safe_float(
            cashflow.iloc[0][operating_cash_col]
        )


    # =====================================================
    # 11. 显示关键数据
    # =====================================================

    st.subheader(
        "💰 最近一期关键数据"
    )


    metric_cols = st.columns(5)


    metric_cols[0].metric(
        "营业收入",
        "暂无"
        if latest_revenue is None
        else f"{latest_revenue:,.2f}"
    )


    metric_cols[1].metric(
        "净利润",
        "暂无"
        if latest_profit is None
        else f"{latest_profit:,.2f}"
    )


    metric_cols[2].metric(
        "经营现金流",
        "暂无"
        if latest_cashflow is None
        else f"{latest_cashflow:,.2f}"
    )


    metric_cols[3].metric(
        "应收账款",
        "暂无"
        if latest_receivable is None
        else f"{latest_receivable:,.2f}"
    )


    metric_cols[4].metric(
        "存货",
        "暂无"
        if latest_inventory is None
        else f"{latest_inventory:,.2f}"
    )


    # =====================================================
    # 12. 利润质量分析
    # =====================================================

    st.subheader(
        "💡 利润质量"
    )


    cash_profit_ratio = safe_ratio(
        latest_cashflow,
        latest_profit
    )


    if cash_profit_ratio is not None:


        st.metric(
            "经营现金流 / 净利润",
            f"{cash_profit_ratio:.2f}"
        )


        if cash_profit_ratio >= 1:

            st.success(
                "✅ 经营现金流能够覆盖净利润，利润现金含量较好。"
            )


        elif cash_profit_ratio >= 0.7:

            st.warning(
                "🟡 经营现金流与净利润基本匹配，但需要持续观察。"
            )


        elif cash_profit_ratio >= 0:

            st.warning(
                "⚠️ 经营现金流明显低于净利润，利润质量需要进一步分析。"
            )


        else:

            st.error(
                "🚨 经营现金流为负，而净利润可能为正，属于重点排雷信号。"
            )


    else:

        st.info(
            "暂无足够数据计算经营现金流/净利润。"
        )


    # =====================================================
    # 13. 应收账款风险
    # =====================================================

    st.subheader(
        "📌 应收账款风险"
    )


    receivable_ratio = None


    if (
        latest_receivable is not None
        and latest_revenue is not None
    ):


        receivable_ratio = (
            latest_receivable
            / latest_revenue
        )


        st.metric(
            "应收账款 / 营业收入",
            f"{receivable_ratio:.2%}"
        )


        if receivable_ratio > 0.40:

            st.error(
                "🚨 应收账款占营业收入比例较高，需要重点检查回款能力。"
            )


        elif receivable_ratio > 0.25:

            st.warning(
                "🟡 应收账款占比较高，需要结合历史趋势判断。"
            )


        else:

            st.success(
                "✅ 应收账款/营业收入比例暂未显示明显异常。"
            )


    else:

        st.info(
            "暂无足够数据进行应收账款比例分析。"
        )


    # =====================================================
    # 14. 存货风险
    # =====================================================

    st.subheader(
        "📦 存货风险"
    )


    inventory_ratio = None


    if (
        latest_inventory is not None
        and latest_revenue is not None
    ):


        inventory_ratio = (
            latest_inventory
            / latest_revenue
        )


        st.metric(
            "存货 / 营业收入",
            f"{inventory_ratio:.2%}"
        )


        if inventory_ratio > 0.50:

            st.error(
                "🚨 存货相对营业规模较高，需要检查库存周转和减值风险。"
            )


        elif inventory_ratio > 0.30:

            st.warning(
                "🟡 存货占比需要继续观察。"
            )


        else:

            st.success(
                "✅ 存货/营业收入比例暂未显示明显异常。"
            )


    else:

        st.info(
            "暂无足够数据进行存货比例分析。"
        )


    # =====================================================
    # 15. 综合财务排雷
    # =====================================================

    st.divider()

    st.subheader(
        "🚨 V6 财务排雷结论"
    )


    risk_score = 0

    risk_items = []


    # 现金流
    if (
        cash_profit_ratio is not None
        and cash_profit_ratio < 0.7
    ):

        risk_score += 2

        risk_items.append(
            "经营现金流与净利润匹配度偏低"
        )


    # 应收账款
    if (
        receivable_ratio is not None
        and receivable_ratio > 0.40
    ):

        risk_score += 2

        risk_items.append(
            "应收账款占营业收入比例较高"
        )


    # 存货
    if (
        inventory_ratio is not None
        and inventory_ratio > 0.50
    ):

        risk_score += 2

        risk_items.append(
            "存货占营业收入比例较高"
        )


    # ROE
    if roe is not None and roe < 10:

        risk_score += 1

        risk_items.append(
            "ROE偏低"
        )


    # 负债率
    if debt_ratio is not None and debt_ratio >= 70:

        risk_score += 2

        risk_items.append(
            "资产负债率偏高"
        )


    # =====================================================
    # 16. 最终风险评级
    # =====================================================

    if risk_score == 0:

        st.success(
            "🟢 当前未发现明显的一级财务风险信号。"
        )


    elif risk_score <= 2:

        st.warning(
            "🟡 当前存在少量需要观察的财务风险。"
        )


    elif risk_score <= 4:

        st.warning(
            "🟠 当前存在多个值得深入研究的风险信号。"
        )


    else:

        st.error(
            "🔴 当前存在较多财务风险信号，不宜仅凭利润增长判断公司质量。"
        )


    if risk_items:

        st.write(
            "### 重点关注"
        )


        for item in risk_items:

            st.write(
                f"- {item}"
            )


# =====================================================
# V7：长期价值投资10步分析
# =====================================================

st.divider()

st.header("🏆 长期价值投资10步分析")

st.caption(
    "本模块基于当前已获取的财务数据进行规则化分析。"
    "行业、护城河、管理层和估值等需要后续接入更多数据后进一步完善。"
)

# -----------------------------------------------------
# 10步分析结果
# -----------------------------------------------------

step_results = []


# =====================================================
# ① 行业与成长空间
# =====================================================

step_results.append({
    "步骤": "① 行业与成长空间",
    "结论": "待增强",
    "说明": "当前版本尚未接入行业规模、行业增速及竞争格局数据。下一阶段加入行业数据库。"
})


# =====================================================
# ② 企业护城河
# =====================================================

step_results.append({
    "步骤": "② 企业护城河",
    "结论": "待增强",
    "说明": "需要结合品牌、成本优势、技术壁垒、渠道、客户粘性等非财务数据判断。"
})


# =====================================================
# ③ 长期营收与净利润成长
# =====================================================

if revenue_growth is not None and profit_growth is not None:

    if revenue_growth > 10 and profit_growth > 10:

        result = "较好"

        explanation = (
            f"当前营收增长率 {revenue_growth:.2f}%，"
            f"净利润增长率 {profit_growth:.2f}%，"
            "当前增长表现较好。"
        )

    elif revenue_growth >= 0 and profit_growth >= 0:

        result = "一般"

        explanation = (
            f"当前营收增长率 {revenue_growth:.2f}%，"
            f"净利润增长率 {profit_growth:.2f}%，"
            "公司仍在增长，但速度一般。"
        )

    else:

        result = "偏弱"

        explanation = (
            f"当前营收增长率 {revenue_growth:.2f}%，"
            f"净利润增长率 {profit_growth:.2f}%，"
            "增长出现压力。"
        )

else:

    result = "数据不足"

    explanation = "缺少足够的增长数据。"


step_results.append({
    "步骤": "③ 长期营收与净利润成长",
    "结论": result,
    "说明": explanation
})


# =====================================================
# ④ ROE及盈利能力
# =====================================================

if roe is not None:

    if roe >= 20:

        result = "优秀"

        explanation = (
            f"ROE {roe:.2f}%，资本回报能力较强。"
        )

    elif roe >= 15:

        result = "良好"

        explanation = (
            f"ROE {roe:.2f}%，盈利能力较好。"
        )

    elif roe >= 10:

        result = "一般"

        explanation = (
            f"ROE {roe:.2f}%，资本使用效率一般。"
        )

    else:

        result = "偏弱"

        explanation = (
            f"ROE {roe:.2f}%，需要重点研究盈利能力。"
        )

else:

    result = "数据不足"

    explanation = "没有获得可用ROE。"


step_results.append({
    "步骤": "④ ROE及盈利能力",
    "结论": result,
    "说明": explanation
})


# =====================================================
# ⑤ 经营现金流与利润匹配度
# =====================================================

if cash_profit_ratio is not None:

    if cash_profit_ratio >= 1:

        result = "优秀"

        explanation = (
            f"经营现金流/净利润 = {cash_profit_ratio:.2f}，"
            "现金流能够覆盖利润。"
        )

    elif cash_profit_ratio >= 0.7:

        result = "良好"

        explanation = (
            f"经营现金流/净利润 = {cash_profit_ratio:.2f}，"
            "总体可以匹配。"
        )

    elif cash_profit_ratio >= 0:

        result = "需要关注"

        explanation = (
            f"经营现金流/净利润 = {cash_profit_ratio:.2f}，"
            "明显低于1，需要继续排查利润质量。"
        )

    else:

        result = "高风险信号"

        explanation = (
            f"经营现金流/净利润 = {cash_profit_ratio:.2f}，"
            "经营现金流为负，需要重点排查。"
        )

else:

    result = "数据不足"

    explanation = "缺少净利润或经营现金流数据。"


step_results.append({
    "步骤": "⑤ 经营现金流与利润匹配度",
    "结论": result,
    "说明": explanation
})


# =====================================================
# ⑥ 资产负债表与偿债能力
# =====================================================

if debt_ratio is not None:

    if debt_ratio < 50:

        result = "优秀"

        explanation = (
            f"资产负债率 {debt_ratio:.2f}%，"
            "整体较稳健。"
        )

    elif debt_ratio < 70:

        result = "良好"

        explanation = (
            f"资产负债率 {debt_ratio:.2f}%，"
            "处于需要持续观察的水平。"
        )

    else:

        result = "偏高"

        explanation = (
            f"资产负债率 {debt_ratio:.2f}%，"
            "杠杆水平较高，需要重点关注偿债能力。"
        )

else:

    result = "数据不足"

    explanation = "没有获得资产负债率。"


step_results.append({
    "步骤": "⑥ 资产负债表与偿债能力",
    "结论": result,
    "说明": explanation
})


# =====================================================
# ⑦ 应收账款和存货质量
# =====================================================

quality_messages = []

quality_result = "正常"

if receivable_ratio is not None:

    if receivable_ratio > 0.40:

        quality_result = "需要关注"

        quality_messages.append(
            f"应收账款/营收 = {receivable_ratio:.2%}，占比较高。"
        )

    else:

        quality_messages.append(
            f"应收账款/营收 = {receivable_ratio:.2%}。"
        )


if inventory_ratio is not None:

    if inventory_ratio > 0.50:

        quality_result = "需要关注"

        quality_messages.append(
            f"存货/营收 = {inventory_ratio:.2%}，占比较高。"
        )

    else:

        quality_messages.append(
            f"存货/营收 = {inventory_ratio:.2%}。"
        )


if not quality_messages:

    quality_messages.append(
        "当前缺少应收账款或存货数据。"
    )

    quality_result = "数据不足"


step_results.append({
    "步骤": "⑦ 应收账款和存货质量",
    "结论": quality_result,
    "说明": " ".join(quality_messages)
})


# =====================================================
# ⑧ 商誉、资本开支及潜在减值
# =====================================================

step_results.append({
    "步骤": "⑧ 商誉、资本开支及潜在减值",
    "结论": "待增强",
    "说明": "下一版本接入商誉、固定资产、在建工程及资本开支数据后自动判断。"
})


# =====================================================
# ⑨ 管理层、股东结构、关联交易
# =====================================================

step_results.append({
    "步骤": "⑨ 管理层、股东结构、关联交易",
    "结论": "待增强",
    "说明": "需要接入股东结构、实际控制人、关联交易及公司公告数据。"
})


# =====================================================
# ⑩ 估值与合理买入价
# =====================================================

step_results.append({
    "步骤": "⑩ 估值与合理买入价",
    "结论": "待增强",
    "说明": "下一阶段加入PE、PB、DCF/盈利估值模型后计算合理价、建仓价、重仓价和高估价。"
})


# =====================================================
# 显示10步分析
# =====================================================

st.subheader("📋 10步分析结果")

for item in step_results:

    with st.expander(
        f"{item['步骤']} —— {item['结论']}"
    ):

        st.write(
            item["说明"]
        )


# =====================================================
# 数据支持度评分
# =====================================================

supported_count = 0

for item in step_results:

    if item["结论"] not in [
        "待增强",
        "数据不足"
    ]:

        supported_count += 1


st.subheader("🎯 当前模型完成度")

completion = (
    supported_count
    / len(step_results)
    * 100
)


st.progress(
    completion / 100
)

st.write(
    f"当前自动化完成度：{completion:.0f}%"
)

st.info(
    "目前系统已经能够自动完成财务维度分析。"
    "行业、护城河、管理层和估值模块将在后续版本逐步接入。"
)


st.divider()

st.caption(
    "V7：正式加入长期价值投资10步分析框架。"
    "当前版本强调数据真实性，不对尚未接入的数据进行虚假评分。"
)
# =====================================================
# V8：5年财务质量综合评分
# =====================================================

st.divider()

st.header("⭐ V8：5年财务质量综合评分")

st.caption(
    "基于最近多个年度的财务指标，判断企业盈利能力、成长性、"
    "财务安全和现金流质量。"
)


# -----------------------------------------------------
# 找日期字段
# -----------------------------------------------------

date_col = None

date_candidates = [
    "日期",
    "报告期",
    "报告日期",
    "截止日期",
    "报告期末"
]

for col in date_candidates:

    if col in indicators.columns:
        date_col = col
        break


# -----------------------------------------------------
# 建立年度数据
# -----------------------------------------------------

trend = indicators.copy()


if date_col is not None:

    trend[date_col] = pd.to_datetime(
        trend[date_col],
        errors="coerce"
    )

    trend = trend.dropna(
        subset=[date_col]
    )

    trend["年份"] = (
        trend[date_col]
        .dt.year
    )

    # 每年保留一条
    trend = (
        trend
        .sort_values(date_col)
        .groupby("年份")
        .tail(1)
    )

    trend = (
        trend
        .sort_values("年份")
        .tail(5)
    )

else:

    # 如果接口没有日期字段，则直接取最近5行
    trend = indicators.head(5).copy()

    trend["年份"] = [
        f"第{i + 1}期"
        for i in range(len(trend))
    ]


# -----------------------------------------------------
# 找关键字段
# -----------------------------------------------------

roe_col_v8 = find_column(
    trend,
    [
        "加权净资产收益率(%)",
        "加权净资产收益率",
        "净资产收益率(%)",
        "净资产收益率"
    ]
)


revenue_growth_col_v8 = find_column(
    trend,
    [
        "主营业务收入增长率(%)",
        "主营业务收入增长率"
    ]
)


profit_growth_col_v8 = find_column(
    trend,
    [
        "净利润增长率(%)",
        "净利润增长率"
    ]
)


debt_col_v8 = find_column(
    trend,
    [
        "资产负债率(%)",
        "资产负债率"
    ]
)


cashflow_col_v8 = find_column(
    trend,
    [
        "每股经营性现金流(元)",
        "每股经营性现金流"
    ]
)


# -----------------------------------------------------
# 提取数据
# -----------------------------------------------------

roe_values = []

revenue_growth_values = []

profit_growth_values = []

debt_values = []

cashflow_values = []


if roe_col_v8:

    roe_values = [
        safe_float(x)
        for x in trend[roe_col_v8]
    ]


if revenue_growth_col_v8:

    revenue_growth_values = [
        safe_float(x)
        for x in trend[revenue_growth_col_v8]
    ]


if profit_growth_col_v8:

    profit_growth_values = [
        safe_float(x)
        for x in trend[profit_growth_col_v8]
    ]


if debt_col_v8:

    debt_values = [
        safe_float(x)
        for x in trend[debt_col_v8]
    ]


if cashflow_col_v8:

    cashflow_values = [
        safe_float(x)
        for x in trend[cashflow_col_v8]
    ]


# -----------------------------------------------------
# 去掉空值
# -----------------------------------------------------

roe_clean = [
    x for x in roe_values
    if x is not None
]


revenue_clean = [
    x for x in revenue_growth_values
    if x is not None
]


profit_clean = [
    x for x in profit_growth_values
    if x is not None
]


debt_clean = [
    x for x in debt_values
    if x is not None
]


cashflow_clean = [
    x for x in cashflow_values
    if x is not None
]


# -----------------------------------------------------
# 显示5年趋势表
# -----------------------------------------------------

display_columns = {}

if roe_col_v8:
    display_columns["ROE"] = trend[roe_col_v8]

if revenue_growth_col_v8:
    display_columns["营收增长率"] = trend[revenue_growth_col_v8]

if profit_growth_col_v8:
    display_columns["净利润增长率"] = trend[profit_growth_col_v8]

if debt_col_v8:
    display_columns["资产负债率"] = trend[debt_col_v8]

if cashflow_col_v8:
    display_columns["每股经营现金流"] = trend[cashflow_col_v8]


if display_columns:

    trend_display = pd.DataFrame(
        display_columns
    )

    trend_display.insert(
        0,
        "年份",
        trend["年份"].astype(str).values
    )

    st.subheader(
        "📅 最近5期核心财务指标"
    )

    st.dataframe(
        trend_display,
        use_container_width=True,
        hide_index=True
    )


# -----------------------------------------------------
# 计算评分
# -----------------------------------------------------

roe_score = 0

growth_score = 0

profit_score = 0

debt_score = 0

cash_score = 0


# =====================================================
# ROE评分 20分
# =====================================================

if roe_clean:

    avg_roe = sum(roe_clean) / len(roe_clean)

    min_roe = min(roe_clean)

    if avg_roe >= 20 and min_roe >= 15:

        roe_score = 20

    elif avg_roe >= 15 and min_roe >= 10:

        roe_score = 17

    elif avg_roe >= 10:

        roe_score = 13

    elif avg_roe >= 5:

        roe_score = 8

    else:

        roe_score = 3


# =====================================================
# 营收成长评分 20分
# =====================================================

if revenue_clean:

    avg_revenue_growth = (
        sum(revenue_clean)
        / len(revenue_clean)
    )

    positive_years = sum(
        1
        for x in revenue_clean
        if x >= 0
    )

    if (
        avg_revenue_growth >= 15
        and positive_years >= 4
    ):

        growth_score = 20

    elif (
        avg_revenue_growth >= 8
        and positive_years >= 4
    ):

        growth_score = 16

    elif avg_revenue_growth >= 0:

        growth_score = 11

    else:

        growth_score = 4


# =====================================================
# 净利润成长评分 20分
# =====================================================

if profit_clean:

    avg_profit_growth = (
        sum(profit_clean)
        / len(profit_clean)
    )

    positive_profit_years = sum(
        1
        for x in profit_clean
        if x >= 0
    )

    if (
        avg_profit_growth >= 20
        and positive_profit_years >= 4
    ):

        profit_score = 20

    elif (
        avg_profit_growth >= 10
        and positive_profit_years >= 4
    ):

        profit_score = 16

    elif avg_profit_growth >= 0:

        profit_score = 11

    else:

        profit_score = 4


# =====================================================
# 财务安全评分 20分
# =====================================================

if debt_clean:

    avg_debt = (
        sum(debt_clean)
        / len(debt_clean)
    )

    debt_change = (
        debt_clean[-1]
        - debt_clean[0]
    )

    if avg_debt < 50 and debt_change <= 5:

        debt_score = 20

    elif avg_debt < 60 and debt_change <= 8:

        debt_score = 17

    elif avg_debt < 70:

        debt_score = 13

    elif avg_debt < 80:

        debt_score = 8

    else:

        debt_score = 3


# =====================================================
# 现金流评分 20分
# =====================================================

if cashflow_clean:

    positive_cashflow_years = sum(
        1
        for x in cashflow_clean
        if x > 0
    )

    avg_cashflow = (
        sum(cashflow_clean)
        / len(cashflow_clean)
    )

    if (
        positive_cashflow_years >= 4
        and avg_cashflow > 0
    ):

        cash_score = 20

    elif positive_cashflow_years >= 3:

        cash_score = 16

    elif positive_cashflow_years >= 2:

        cash_score = 10

    elif avg_cashflow > 0:

        cash_score = 7

    else:

        cash_score = 3


# -----------------------------------------------------
# 总分
# -----------------------------------------------------

financial_quality_score = (
    roe_score
    + growth_score
    + profit_score
    + debt_score
    + cash_score
)


# -----------------------------------------------------
# 综合评级
# -----------------------------------------------------

if financial_quality_score >= 85:

    financial_rating = "优秀"

elif financial_quality_score >= 75:

    financial_rating = "良好"

elif financial_quality_score >= 60:

    financial_rating = "一般"

else:

    financial_rating = "偏弱"


# -----------------------------------------------------
# 显示评分
# -----------------------------------------------------

st.subheader(
    "🎯 财务质量评分"
)


score_col1, score_col2 = st.columns(2)


score_col1.metric(
    "财务质量总分",
    f"{financial_quality_score} / 100"
)


score_col2.metric(
    "综合评级",
    financial_rating
)


# -----------------------------------------------------
# 分项评分
# -----------------------------------------------------

st.subheader(
    "📊 分项评分"
)


score_table = pd.DataFrame({
    "项目": [
        "ROE及盈利能力",
        "营收成长",
        "净利润成长",
        "财务安全",
        "现金流质量"
    ],
    "得分": [
        f"{roe_score}/20",
        f"{growth_score}/20",
        f"{profit_score}/20",
        f"{debt_score}/20",
        f"{cash_score}/20"
    ]
})


st.dataframe(
    score_table,
    use_container_width=True,
    hide_index=True
)


# -----------------------------------------------------
# 趋势解读
# -----------------------------------------------------

st.subheader(
    "🔍 五年趋势解读"
)


if roe_clean:

    st.write(
        f"**ROE：** 最近5期平均 "
        f"{sum(roe_clean) / len(roe_clean):.2f}%"
    )


if revenue_clean:

    st.write(
        f"**营收增长：** 最近5期平均 "
        f"{sum(revenue_clean) / len(revenue_clean):.2f}%"
    )


if profit_clean:

    st.write(
        f"**净利润增长：** 最近5期平均 "
        f"{sum(profit_clean) / len(profit_clean):.2f}%"
    )


if debt_clean:

    st.write(
        f"**资产负债率：** 最近一期 "
        f"{debt_clean[-1]:.2f}%"
    )


if cashflow_clean:

    positive_years = sum(
        1
        for x in cashflow_clean
        if x > 0
    )

    st.write(
        f"**经营现金流：** 最近5期中有 "
        f"{positive_years} 期为正"
    )


# -----------------------------------------------------
# 最终判断
# -----------------------------------------------------

st.subheader(
    "🏆 V8财务质量结论"
)


if financial_quality_score >= 85:

    st.success(
        "🟢 财务质量优秀："
        "盈利能力、成长性、财务安全和现金流整体表现较强。"
    )

elif financial_quality_score >= 75:

    st.success(
        "🟢 财务质量良好："
        "整体具备较好的长期财务基础，但仍需结合估值和行业竞争力判断。"
    )

elif financial_quality_score >= 60:

    st.warning(
        "🟡 财务质量一般："
        "部分核心指标表现尚可，但存在需要进一步研究的地方。"
    )

else:

    st.error(
        "🔴 财务质量偏弱："
        "不建议仅凭短期利润增长做长期投资判断。"
    )


st.info(
    "注意：V8是规则化财务评分，不代表股票未来收益率。"
    "下一阶段将加入估值、行业比较和护城河分析。"
)
# =====================================================
# V9：价值估值系统
# =====================================================

st.divider()

st.header("💰 V9：价值估值系统")

st.caption(
    "基于当前价格、EPS、每股净资产及目标PE/PB进行情景估值。"
    "该模块用于研究和估值敏感性分析，不代表未来股价预测。"
)


# =====================================================
# 1. 获取当前价格
# =====================================================

valuation_price = None

try:

    if history is not None and not history.empty:

        valuation_price = float(
            history.iloc[-1]["close"]
        )

except Exception:

    valuation_price = None


# =====================================================
# 2. 寻找 EPS
# =====================================================

eps_col = find_column(
    indicators,
    [
        "摊薄每股收益(元)",
        "摊薄每股收益",
        "基本每股收益(元)",
        "基本每股收益",
        "每股收益(元)",
        "每股收益"
    ]
)


# =====================================================
# 3. 寻找每股净资产
# =====================================================

bvps_col = find_column(
    indicators,
    [
        "每股净资产(元)",
        "每股净资产",
        "股东权益比率",
        "归属母公司股东的每股净资产"
    ]
)


latest_eps = None

latest_bvps = None


if eps_col:

    latest_eps = safe_float(
        indicators.iloc[0][eps_col]
    )


if bvps_col:

    latest_bvps = safe_float(
        indicators.iloc[0][bvps_col]
    )


# =====================================================
# 4. 当前估值
# =====================================================

st.subheader(
    "📊 当前估值基础数据"
)


v1, v2, v3, v4 = st.columns(4)


v1.metric(
    "当前参考价",
    "暂无"
    if valuation_price is None
    else f"{valuation_price:.2f} 元"
)


v2.metric(
    "最新EPS",
    "暂无"
    if latest_eps is None
    else f"{latest_eps:.2f} 元"
)


v3.metric(
    "每股净资产",
    "暂无"
    if latest_bvps is None
    else f"{latest_bvps:.2f} 元"
)


current_pe = None

current_pb = None


if (
    valuation_price is not None
    and latest_eps is not None
    and latest_eps > 0
):

    current_pe = (
        valuation_price
        / latest_eps
    )


if (
    valuation_price is not None
    and latest_bvps is not None
    and latest_bvps > 0
):

    current_pb = (
        valuation_price
        / latest_bvps
    )


v4.metric(
    "当前PE",
    "暂无"
    if current_pe is None
    else f"{current_pe:.2f}"
)


st.write(
    "当前PB："
    + (
        "暂无"
        if current_pb is None
        else f"{current_pb:.2f}"
    )
)


# =====================================================
# 5. 估值参数
# =====================================================

st.subheader(
    "⚙️ 估值参数"
)

st.caption(
    "下面参数不是程序强行决定的，而是允许你根据公司质量和行业特点调整。"
)


# -----------------------------------------------------
# 默认参数
# -----------------------------------------------------

default_pe_conservative = 12.0

default_pe_normal = 16.0

default_pe_optimistic = 20.0


if roe is not None:

    if roe >= 20:

        default_pe_conservative = 15.0
        default_pe_normal = 20.0
        default_pe_optimistic = 25.0

    elif roe >= 15:

        default_pe_conservative = 13.0
        default_pe_normal = 17.0
        default_pe_optimistic = 22.0

    elif roe >= 10:

        default_pe_conservative = 10.0
        default_pe_normal = 14.0
        default_pe_optimistic = 18.0


col_a, col_b, col_c = st.columns(3)


pe_conservative = col_a.number_input(
    "保守目标PE",
    min_value=5.0,
    max_value=50.0,
    value=default_pe_conservative,
    step=1.0
)


pe_normal = col_b.number_input(
    "中性目标PE",
    min_value=5.0,
    max_value=50.0,
    value=default_pe_normal,
    step=1.0
)


pe_optimistic = col_c.number_input(
    "乐观目标PE",
    min_value=5.0,
    max_value=50.0,
    value=default_pe_optimistic,
    step=1.0
)


# =====================================================
# 6. PE估值
# =====================================================

pe_conservative_value = None

pe_normal_value = None

pe_optimistic_value = None


if latest_eps is not None and latest_eps > 0:

    pe_conservative_value = (
        latest_eps
        * pe_conservative
    )

    pe_normal_value = (
        latest_eps
        * pe_normal
    )

    pe_optimistic_value = (
        latest_eps
        * pe_optimistic
    )


st.subheader(
    "📈 PE情景估值"
)


pe_table = pd.DataFrame({

    "情景": [
        "保守",
        "中性",
        "乐观"
    ],

    "目标PE": [
        pe_conservative,
        pe_normal,
        pe_optimistic
    ],

    "估算价格": [
        pe_conservative_value,
        pe_normal_value,
        pe_optimistic_value
    ]

})


if pe_conservative_value is not None:

    pe_table["估算价格"] = (
        pe_table["估算价格"]
        .round(2)
    )


st.dataframe(
    pe_table,
    use_container_width=True,
    hide_index=True
)


# =====================================================
# 7. PB估值
# =====================================================

pb_conservative = st.number_input(
    "保守目标PB",
    min_value=0.5,
    max_value=10.0,
    value=1.2,
    step=0.1
)


pb_normal = st.number_input(
    "中性目标PB",
    min_value=0.5,
    max_value=10.0,
    value=1.8,
    step=0.1
)


pb_optimistic = st.number_input(
    "乐观目标PB",
    min_value=0.5,
    max_value=10.0,
    value=2.5,
    step=0.1
)


pb_conservative_value = None

pb_normal_value = None

pb_optimistic_value = None


if latest_bvps is not None and latest_bvps > 0:

    pb_conservative_value = (
        latest_bvps
        * pb_conservative
    )

    pb_normal_value = (
        latest_bvps
        * pb_normal
    )

    pb_optimistic_value = (
        latest_bvps
        * pb_optimistic
    )


st.subheader(
    "📚 PB情景估值"
)


pb_table = pd.DataFrame({

    "情景": [
        "保守",
        "中性",
        "乐观"
    ],

    "目标PB": [
        pb_conservative,
        pb_normal,
        pb_optimistic
    ],

    "估算价格": [
        pb_conservative_value,
        pb_normal_value,
        pb_optimistic_value
    ]

})


if pb_conservative_value is not None:

    pb_table["估算价格"] = (
        pb_table["估算价格"]
        .round(2)
    )


st.dataframe(
    pb_table,
    use_container_width=True,
    hide_index=True
)


# =====================================================
# 8. PE + PB综合估值
# =====================================================

st.subheader(
    "🎯 综合估值"
)


# -----------------------------------------------------
# 根据ROE决定PE/PB权重
# -----------------------------------------------------

if roe is not None and roe >= 15:

    pe_weight = 0.7

    pb_weight = 0.3

elif roe is not None and roe >= 10:

    pe_weight = 0.6

    pb_weight = 0.4

else:

    pe_weight = 0.5

    pb_weight = 0.5


st.write(
    f"当前模型权重：PE {pe_weight:.0%} / PB {pb_weight:.0%}"
)


conservative_value = None

normal_value = None

optimistic_value = None


if (
    pe_conservative_value is not None
    and pb_conservative_value is not None
):

    conservative_value = (
        pe_conservative_value * pe_weight
        + pb_conservative_value * pb_weight
    )


if (
    pe_normal_value is not None
    and pb_normal_value is not None
):

    normal_value = (
        pe_normal_value * pe_weight
        + pb_normal_value * pb_weight
    )


if (
    pe_optimistic_value is not None
    and pb_optimistic_value is not None
):

    optimistic_value = (
        pe_optimistic_value * pe_weight
        + pb_optimistic_value * pb_weight
    )


valuation_table = pd.DataFrame({

    "估值情景": [
        "保守",
        "中性",
        "乐观"
    ],

    "综合估算价格": [
        conservative_value,
        normal_value,
        optimistic_value
    ]

})


if conservative_value is not None:

    valuation_table[
        "综合估算价格"
    ] = (
        valuation_table[
            "综合估算价格"
        ]
        .round(2)
    )


st.dataframe(
    valuation_table,
    use_container_width=True,
    hide_index=True
)


# =====================================================
# 9. 建仓价 / 重仓价 / 高估价
# =====================================================

st.subheader(
    "💰 投资价格区间"
)


entry_price = None

heavy_position_price = None

high_valuation_price = None


if normal_value is not None:

    # 建仓：合理价值的85%
    entry_price = (
        normal_value
        * 0.85
    )

    # 重仓：合理价值的70%
    heavy_position_price = (
        normal_value
        * 0.70
    )


if conservative_value is not None:

    high_valuation_price = (
        optimistic_value
    )


p1, p2, p3, p4 = st.columns(4)


p1.metric(
    "建仓参考价",
    "暂无"
    if entry_price is None
    else f"{entry_price:.2f} 元"
)


p2.metric(
    "重仓参考价",
    "暂无"
    if heavy_position_price is None
    else f"{heavy_position_price:.2f} 元"
)


p3.metric(
    "中性合理价",
    "暂无"
    if normal_value is None
    else f"{normal_value:.2f} 元"
)


p4.metric(
    "高估参考价",
    "暂无"
    if high_valuation_price is None
    else f"{high_valuation_price:.2f} 元"
)


# =====================================================
# 10. 当前价格判断
# =====================================================

st.subheader(
    "🔍 当前价格判断"
)


if (
    valuation_price is not None
    and normal_value is not None
):

    discount = (
        normal_value
        / valuation_price
        - 1
    ) * 100


    st.metric(
        "相对中性合理价值空间",
        f"{discount:.2f}%"
    )


    if valuation_price <= heavy_position_price:

        st.success(
            "🟢 当前价格进入模型重仓价值区间。"
        )

    elif valuation_price <= entry_price:

        st.success(
            "🟢 当前价格进入模型建仓区间。"
        )

    elif valuation_price <= normal_value:

        st.info(
            "🟡 当前价格低于模型中性合理价值，但安全边际一般。"
        )

    elif valuation_price <= optimistic_value:

        st.warning(
            "🟠 当前价格高于中性合理价值，建议等待更好的安全边际。"
        )

    else:

        st.error(
            "🔴 当前价格超过乐观估值区间，模型认为估值偏高。"
        )

else:

    st.warning(
        "⚠️ 当前数据不足，暂时无法完成PE/PB估值。"
    )


# =====================================================
# 11. 估值风险提示
# =====================================================

st.subheader(
    "⚠️ 估值模型风险提示"
)


st.write(
    "1. PE估值高度依赖未来盈利的稳定性。"
)

st.write(
    "2. PB估值对资产质量和ROE非常敏感。"
)

st.write(
    "3. 周期股、强周期行业和利润波动较大的公司，不宜简单套用固定PE。"
)

st.write(
    "4. 当前V9还没有加入DCF、行业估值分位数和同行业估值比较。"
)

st.write(
    "5. 因此当前价格区间属于模型参考值，不应单独作为买卖依据。"
)


st.divider()

st.caption(
    "V9：PE + PB情景估值。下一阶段将加入行业估值、DCF及综合投资评级。"
)
# =====================================================
# V10：综合投资决策引擎
# =====================================================

st.divider()

st.header("🏆 V10：ValueStock AI 综合投资评级")

st.caption(
    "综合财务质量、成长性、现金流、财务安全和估值进行规则化评分。"
    "尚未量化的行业、护城河和管理层部分不会被虚假打分。"
)


# =====================================================
# 1. 安全读取前面模块的数据
# =====================================================

financial_score = globals().get(
    "financial_quality_score",
    None
)

financial_rating = globals().get(
    "financial_rating",
    "数据不足"
)

current_price = globals().get(
    "valuation_price",
    None
)

normal_value_v10 = globals().get(
    "normal_value",
    None
)

entry_price_v10 = globals().get(
    "entry_price",
    None
)

heavy_price_v10 = globals().get(
    "heavy_position_price",
    None
)

high_price_v10 = globals().get(
    "high_valuation_price",
    None
)

roe_v10 = globals().get(
    "roe",
    None
)

revenue_growth_v10 = globals().get(
    "revenue_growth",
    None
)

profit_growth_v10 = globals().get(
    "profit_growth",
    None
)

debt_ratio_v10 = globals().get(
    "debt_ratio",
    None
)

cash_profit_ratio_v10 = globals().get(
    "cash_profit_ratio",
    None
)

risk_score_v10 = globals().get(
    "risk_score",
    0
)

risk_items_v10 = globals().get(
    "risk_items",
    []
)


# =====================================================
# 2. 六大维度评分
# =====================================================

# 财务质量：30分
financial_component = 0

if financial_score is not None:

    financial_component = (
        financial_score
        * 0.30
    )


# 成长性：20分
growth_component = 0

if (
    revenue_growth_v10 is not None
    and profit_growth_v10 is not None
):

    growth_avg = (
        revenue_growth_v10
        + profit_growth_v10
    ) / 2

    if growth_avg >= 20:

        growth_component = 20

    elif growth_avg >= 15:

        growth_component = 17

    elif growth_avg >= 10:

        growth_component = 14

    elif growth_avg >= 5:

        growth_component = 10

    elif growth_avg >= 0:

        growth_component = 6

    else:

        growth_component = 2


# 盈利能力：15分
profitability_component = 0

if roe_v10 is not None:

    if roe_v10 >= 20:

        profitability_component = 15

    elif roe_v10 >= 15:

        profitability_component = 13

    elif roe_v10 >= 10:

        profitability_component = 10

    elif roe_v10 >= 5:

        profitability_component = 6

    else:

        profitability_component = 2


# 现金流质量：15分
cash_component = 0

if cash_profit_ratio_v10 is not None:

    if cash_profit_ratio_v10 >= 1.0:

        cash_component = 15

    elif cash_profit_ratio_v10 >= 0.8:

        cash_component = 13

    elif cash_profit_ratio_v10 >= 0.6:

        cash_component = 10

    elif cash_profit_ratio_v10 >= 0.3:

        cash_component = 6

    elif cash_profit_ratio_v10 >= 0:

        cash_component = 3

    else:

        cash_component = 0


# 财务安全：10分
safety_component = 0

if debt_ratio_v10 is not None:

    if debt_ratio_v10 < 40:

        safety_component = 10

    elif debt_ratio_v10 < 50:

        safety_component = 9

    elif debt_ratio_v10 < 60:

        safety_component = 7

    elif debt_ratio_v10 < 70:

        safety_component = 5

    else:

        safety_component = 2


# 估值：10分
valuation_component = 0

valuation_gap = None

if (
    current_price is not None
    and normal_value_v10 is not None
    and normal_value_v10 > 0
):

    valuation_gap = (
        normal_value_v10
        / current_price
        - 1
    ) * 100


    if valuation_gap >= 30:

        valuation_component = 10

    elif valuation_gap >= 20:

        valuation_component = 9

    elif valuation_gap >= 10:

        valuation_component = 8

    elif valuation_gap >= 0:

        valuation_component = 6

    elif valuation_gap >= -10:

        valuation_component = 4

    elif valuation_gap >= -20:

        valuation_component = 2

    else:

        valuation_component = 0


# =====================================================
# 3. 风险扣分
# =====================================================

risk_penalty = 0

if risk_score_v10 >= 6:

    risk_penalty = 12

elif risk_score_v10 >= 4:

    risk_penalty = 8

elif risk_score_v10 >= 2:

    risk_penalty = 4

else:

    risk_penalty = 0


# =====================================================
# 4. 综合评分
# =====================================================

raw_total = (
    financial_component
    + growth_component
    + profitability_component
    + cash_component
    + safety_component
    + valuation_component
)

final_score = max(
    0,
    min(
        100,
        round(
            raw_total - risk_penalty
        )
    )
)


# =====================================================
# 5. 综合评级
# =====================================================

if final_score >= 85:

    final_rating = "A：优秀长期价值候选"

elif final_score >= 75:

    final_rating = "B：优质，值得长期跟踪"

elif final_score >= 65:

    final_rating = "C：一般，等待更多验证"

elif final_score >= 50:

    final_rating = "D：谨慎，暂不适合重仓"

else:

    final_rating = "E：风险较高"


# =====================================================
# 6. 显示综合评分
# =====================================================

st.subheader(
    "🎯 综合评分"
)


score_col1, score_col2 = st.columns(2)


score_col1.metric(
    "ValueStock AI 综合分",
    f"{final_score} / 100"
)


score_col2.metric(
    "投资评级",
    final_rating
)


# =====================================================
# 7. 分项评分表
# =====================================================

st.subheader(
    "📊 综合评分构成"
)


component_table = pd.DataFrame({

    "分析维度": [
        "财务质量",
        "成长性",
        "盈利能力",
        "现金流质量",
        "财务安全",
        "估值"
    ],

    "满分": [
        30,
        20,
        15,
        15,
        10,
        10
    ],

    "得分": [
        round(financial_component, 1),
        growth_component,
        profitability_component,
        cash_component,
        safety_component,
        valuation_component
    ]

})


st.dataframe(
    component_table,
    use_container_width=True,
    hide_index=True
)


# =====================================================
# 8. 当前投资状态
# =====================================================

st.subheader(
    "💰 当前投资状态"
)


if current_price is not None:

    st.metric(
        "当前参考价格",
        f"{current_price:.2f} 元"
    )


price_table = pd.DataFrame({

    "价格类型": [
        "重仓参考价",
        "建仓参考价",
        "中性合理价",
        "高估参考价"
    ],

    "价格": [
        heavy_price_v10,
        entry_price_v10,
        normal_value_v10,
        high_price_v10
    ]

})


if not price_table.empty:

    price_table["价格"] = (
        price_table["价格"]
        .apply(
            lambda x:
            "暂无"
            if x is None
            else f"{x:.2f}"
        )
    )


st.dataframe(
    price_table,
    use_container_width=True,
    hide_index=True
)


# =====================================================
# 9. 当前价格与合理价值
# =====================================================

st.subheader(
    "🔍 当前价格判断"
)


if valuation_gap is not None:

    if valuation_gap >= 30:

        st.success(
            f"🟢 当前价格相对中性估值存在 "
            f"{valuation_gap:.1f}% 的安全边际。"
        )

    elif valuation_gap >= 15:

        st.success(
            f"🟢 当前价格低于中性合理价值约 "
            f"{valuation_gap:.1f}%。"
        )

    elif valuation_gap >= 0:

        st.info(
            f"🟡 当前价格接近合理价值，"
            f"安全边际约 {valuation_gap:.1f}%。"
        )

    elif valuation_gap >= -15:

        st.warning(
            f"🟠 当前价格高于中性估值约 "
            f"{abs(valuation_gap):.1f}%。"
        )

    else:

        st.error(
            f"🔴 当前价格明显高于中性估值，"
            f"估值风险较大。"
        )

else:

    st.warning(
        "⚠️ 暂时无法计算当前价格与合理价值的差距。"
    )


# =====================================================
# 10. 投资结论
# =====================================================

st.subheader(
    "🏆 ValueStock AI 投资结论"
)


if final_score >= 85:

    conclusion = (
        "公司当前综合质量优秀，财务基础、盈利能力和成长性较强。"
        "若估值处于合理或低估区域，可进入长期重点研究名单。"
    )

elif final_score >= 75:

    conclusion = (
        "公司综合质量较好，具备长期跟踪价值。"
        "投资重点应放在估值和未来盈利增长的持续性。"
    )

elif final_score >= 65:

    conclusion = (
        "公司具备一定投资价值，但多个维度仍需进一步验证。"
        "建议等待更明确的经营改善或更好的安全边际。"
    )

elif final_score >= 50:

    conclusion = (
        "公司存在一定投资风险，当前不宜仅依据短期利润增长进行重仓。"
    )

else:

    conclusion = (
        "当前综合质量和风险收益比较弱，暂不建议作为长期核心资产。"
    )


st.info(
    conclusion
)


# =====================================================
# 11. 风险清单
# =====================================================

if risk_items_v10:

    st.subheader(
        "⚠️ 重点风险"
    )

    for item in risk_items_v10:

        st.write(
            f"• {item}"
        )


# =====================================================
# 12. 数据完整度
# =====================================================

st.subheader(
    "📌 模型数据完整度"
)


available_items = 0

total_items = 8


if financial_score is not None:
    available_items += 1

if roe_v10 is not None:
    available_items += 1

if revenue_growth_v10 is not None:
    available_items += 1

if profit_growth_v10 is not None:
    available_items += 1

if debt_ratio_v10 is not None:
    available_items += 1

if cash_profit_ratio_v10 is not None:
    available_items += 1

if current_price is not None:
    available_items += 1

if normal_value_v10 is not None:
    available_items += 1


data_completeness = (
    available_items
    / total_items
    * 100
)


st.progress(
    data_completeness / 100
)

st.write(
    f"当前关键数据完整度："
    f"{data_completeness:.0f}%"
)


st.caption(
    "V10目前为规则化投资决策模型。"
    "行业竞争格局、护城河、管理层、公告事件、同行估值及DCF尚未完全纳入。"
)
