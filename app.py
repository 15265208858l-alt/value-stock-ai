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
