import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np

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
# 基础函数
# =========================================================

def get_market_code(stock_code):
    if stock_code.startswith(("6", "68")):
        return "sh" + stock_code
    elif stock_code.startswith(("0", "3")):
        return "sz" + stock_code
    elif stock_code.startswith(("4", "8")):
        return "bj" + stock_code
    return stock_code


def get_history_data(stock_code):
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
    data = ak.stock_financial_analysis_indicator(
        symbol=stock_code
    )

    if data is None or data.empty:
        return None

    return data


def get_financial_report(stock_code, report_type):
    market_code = get_market_code(stock_code)

    data = ak.stock_financial_report_sina(
        stock=market_code,
        symbol=report_type
    )

    if data is None or data.empty:
        return None

    return data


def safe_float(value):
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

    for col in candidates:
        if col in df.columns:
            return col

    return None


def normalize_number_series(series):

    result = []

    for value in series:

        number = safe_float(value)

        result.append(number)

    return result


def growth_rate(first, last):

    if first is None or last is None:
        return None

    if first == 0:
        return None

    return (last / first - 1) * 100


def safe_ratio(a, b):

    if a is None or b is None:
        return None

    if b == 0:
        return None

    return a / b


def classify_growth_gap(
    revenue_growth,
    receivable_growth
):

    if (
        revenue_growth is None
        or receivable_growth is None
    ):
        return "数据不足"

    gap = receivable_growth - revenue_growth

    if gap >= 20:
        return "高风险信号"

    elif gap >= 10:
        return "需要关注"

    elif gap >= 0:
        return "基本正常"

    else:
        return "较好"


def classify_profit_cash(
    profit_growth,
    cash_growth
):

    if (
        profit_growth is None
        or cash_growth is None
    ):
        return "数据不足"

    gap = profit_growth - cash_growth

    if gap >= 30:
        return "高风险信号"

    elif gap >= 15:
        return "需要关注"

    elif gap >= -10:
        return "基本匹配"

    else:
        return "现金流表现更强"


def extract_report_years(
    df,
    date_candidates
):

    data = df.copy()

    date_col = find_column(
        data,
        date_candidates
    )

    if date_col is None:
        return data

    data[date_col] = pd.to_datetime(
        data[date_col],
        errors="coerce"
    )

    data = data.dropna(
        subset=[date_col]
    )

    if data.empty:
        return data

    data["年份"] = (
        data[date_col]
        .dt.year
    )

    return data


def select_recent_years(
    df,
    max_years=5
):

    if "年份" not in df.columns:
        return df

    data = (
        df.sort_values("年份")
        .groupby("年份")
        .tail(1)
    )

    return data.tail(max_years)


# =========================================================
# 输入
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
    # 1. 历史行情
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

    except Exception as e:

        st.error(
            "❌ 历史行情获取失败"
        )

        st.code(str(e))


    # =====================================================
    # 2. 获取财务指标
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


        roe_col = find_column(
            indicators,
            [
                "加权净资产收益率(%)",
                "加权净资产收益率",
                "净资产收益率(%)",
                "净资产收益率"
            ]
        )


        revenue_growth_col = find_column(
            indicators,
            [
                "主营业务收入增长率(%)",
                "主营业务收入增长率"
            ]
        )


        profit_growth_col = find_column(
            indicators,
            [
                "净利润增长率(%)",
                "净利润增长率"
            ]
        )


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

        st.code(str(e))

        st.stop()


    # =====================================================
    # 3. 三张财务报表
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

        st.code(str(e))

        st.stop()


    # =====================================================
    # 4. 显示报表字段
    # =====================================================

    with st.expander(
        "查看原始财务报表"
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
    # 5. 自动寻找关键财务字段
    # =====================================================

    st.divider()

    st.subheader(
        "🔎 财务排雷核心检查"
    )


    # -----------------------------------------------------
    # 利润表
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # 资产负债表
    # -----------------------------------------------------

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


    total_assets_col = find_column(
        balance,
        [
            "资产总计",
            "总资产"
        ]
    )


    total_liability_col = find_column(
        balance,
        [
            "负债合计",
            "负债总计"
        ]
    )


    # -----------------------------------------------------
    # 现金流量表
    # -----------------------------------------------------

    operating_cash_col = find_column(
        cashflow,
        [
            "经营活动产生的现金流量净额",
            "经营活动现金流量净额"
        ]
    )


    # =====================================================
    # 6. 最近报告期关键数据
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
    # 7. 利润质量
    # =====================================================

    st.divider()

    st.subheader(
        "💡 利润质量"
    )


    cash_profit_ratio = safe_ratio(
        latest_cashflow,
        latest_profit
    )


    if (
        cash_profit_ratio is not None
        and latest_profit is not None
    ):

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
    # 8. 应收账款风险
    # =====================================================

    st.subheader(
        "📌 应收账款风险"
    )


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
    # 9. 存货风险
    # =====================================================

    st.subheader(
        "📦 存货风险"
    )


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
    # 10. 综合排雷
    # =====================================================

    st.divider()

    st.subheader(
        "🚨 V6财务排雷结论"
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
            "### 重点关注："
        )

        for item in risk_items:

            st.write(
                f"- {item}"
            )


st.divider()

st.caption(
    "V6：利润质量、经营现金流、应收账款、存货及财务风险初步排查。"
    "风险提示仅用于研究，不构成投资建议。"
)
