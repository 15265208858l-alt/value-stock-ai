import streamlit as st
import akshare as ak
import pandas as pd

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("A股长期价值投资财务分析 V4")

st.divider()


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


def get_financial_report(stock_code, report_type):

    market_code = get_market_code(stock_code)

    data = ak.stock_financial_report_sina(
        stock=market_code,
        symbol=report_type
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


def safe_float(value):

    try:

        if value is None:
            return None

        value = str(value).strip()

        if value in ["", "--", "nan", "None"]:
            return None

        value = value.replace(",", "")

        return float(value)

    except Exception:

        return None


def find_column(df, candidates):

    for column in candidates:

        if column in df.columns:
            return column

    return None


stock_code = st.text_input(
    "请输入A股股票代码",
    placeholder="例如：600089、000333、601899"
)


if st.button(
    "开始深度财务分析",
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
        f"正在分析 {stock_code}，请稍候……"
    )


    # =====================================================
    # 1. 行情
    # =====================================================

    try:

        history = get_history_data(stock_code)

        if history is not None:

            latest = history.iloc[-1]

            st.success(
                "✅ A股历史行情获取成功"
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "最新收盘价",
                f"{float(latest['close']):.2f}"
            )

            col2.metric(
                "最新交易日",
                str(latest["date"])
            )

            col3.metric(
                "最高价",
                f"{float(latest['high']):.2f}"
            )

            col4.metric(
                "最低价",
                f"{float(latest['low']):.2f}"
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
    # 2. 财务指标
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


        st.subheader(
            "📊 核心财务指标"
        )


        latest = indicators.iloc[0]


        roe_col = find_column(
            indicators,
            [
                "加权净资产收益率(%)",
                "加权净资产收益率",
                "净资产收益率(%)",
                "净资产收益率"
            ]
        )


        gross_col = find_column(
            indicators,
            [
                "销售毛利率(%)",
                "销售毛利率"
            ]
        )


        net_col = find_column(
            indicators,
            [
                "销售净利率(%)",
                "销售净利率"
            ]
        )


        revenue_col = find_column(
            indicators,
            [
                "主营业务收入增长率(%)",
                "主营业务收入增长率"
            ]
        )


        profit_col = find_column(
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


        cash_col = find_column(
            indicators,
            [
                "每股经营性现金流(元)",
                "每股经营性现金流"
            ]
        )


        roe = safe_float(
            latest[roe_col]
        ) if roe_col else None

        gross_margin = safe_float(
            latest[gross_col]
        ) if gross_col else None

        net_margin = safe_float(
            latest[net_col]
        ) if net_col else None

        revenue_growth = safe_float(
            latest[revenue_col]
        ) if revenue_col else None

        profit_growth = safe_float(
            latest[profit_col]
        ) if profit_col else None

        debt_ratio = safe_float(
            latest[debt_col]
        ) if debt_col else None

        operating_cashflow = safe_float(
            latest[cash_col]
        ) if cash_col else None


        col1, col2, col3 = st.columns(3)


        col1.metric(
            "ROE",
            "暂无" if roe is None
            else f"{roe:.2f}%"
        )


        col2.metric(
            "毛利率",
            "暂无" if gross_margin is None
            else f"{gross_margin:.2f}%"
        )


        col3.metric(
            "净利率",
            "暂无" if net_margin is None
            else f"{net_margin:.2f}%"
        )


        col4, col5, col6 = st.columns(3)


        col4.metric(
            "营收增长率",
            "暂无" if revenue_growth is None
            else f"{revenue_growth:.2f}%"
        )


        col5.metric(
            "净利润增长率",
            "暂无" if profit_growth is None
            else f"{profit_growth:.2f}%"
        )


        col6.metric(
            "资产负债率",
            "暂无" if debt_ratio is None
            else f"{debt_ratio:.2f}%"
        )


        if operating_cashflow is not None:

            st.metric(
                "每股经营现金流",
                f"{operating_cashflow:.2f} 元"
            )


        # =====================================================
        # 3. 财务质量判断
        # =====================================================

        st.divider()

        st.subheader(
            "🔍 财务质量深度判断"
        )


        score = 0

        risk_messages = []

        positive_messages = []


        # -----------------------------
        # ROE
        # -----------------------------

        if roe is not None:

            if roe >= 20:

                score += 25

                positive_messages.append(
                    "✅ ROE达到20%以上，盈利能力较强。"
                )

            elif roe >= 15:

                score += 20

                positive_messages.append(
                    "✅ ROE达到15%以上，具备较好的资本回报能力。"
                )

            elif roe >= 10:

                score += 12

                risk_messages.append(
                    "🟡 ROE处于一般水平，需要继续观察。"
                )

            else:

                score += 5

                risk_messages.append(
                    "⚠️ ROE偏低，企业资本使用效率一般。"
                )


        # -----------------------------
        # 营收增长
        # -----------------------------

        if revenue_growth is not None:

            if revenue_growth >= 15:

                score += 20

                positive_messages.append(
                    "✅ 营收增长较快，业务扩张能力较强。"
                )

            elif revenue_growth >= 5:

                score += 14

                positive_messages.append(
                    "🟡 营收保持增长，但速度中等。"
                )

            elif revenue_growth >= 0:

                score += 8

                risk_messages.append(
                    "🟡 营收增长较弱。"
                )

            else:

                score += 3

                risk_messages.append(
                    "🚨 营收出现负增长。"
                )


        # -----------------------------
        # 净利润增长
        # -----------------------------

        if profit_growth is not None:

            if profit_growth >= 20:

                score += 20

                positive_messages.append(
                    "✅ 净利润增长较快。"
                )

            elif profit_growth >= 10:

                score += 15

                positive_messages.append(
                    "✅ 净利润保持较好的增长。"
                )

            elif profit_growth >= 0:

                score += 8

                risk_messages.append(
                    "🟡 净利润增长一般。"
                )

            else:

                score += 3

                risk_messages.append(
                    "🚨 净利润出现负增长。"
                )


        # -----------------------------
        # 资产负债率
        # -----------------------------

        if debt_ratio is not None:

            if debt_ratio < 50:

                score += 20

                positive_messages.append(
                    "✅ 资产负债率较稳健。"
                )

            elif debt_ratio < 70:

                score += 12

                risk_messages.append(
                    "🟡 资产负债率处于需要观察的水平。"
                )

            else:

                score += 5

                risk_messages.append(
                    "🚨 资产负债率偏高，偿债风险需要重点关注。"
                )


        # -----------------------------
        # 经营现金流
        # -----------------------------

        if operating_cashflow is not None:

            if operating_cashflow > 0:

                score += 15

                positive_messages.append(
                    "✅ 每股经营现金流为正。"
                )

            else:

                risk_messages.append(
                    "🚨 每股经营现金流为负，需要重点排查利润质量。"
                )


        # =====================================================
        # 4. 综合评分
        # =====================================================

        st.subheader(
            "🎯 财务质量评分"
        )


        if score >= 85:

            rating = "优秀"

        elif score >= 70:

            rating = "良好"

        elif score >= 55:

            rating = "一般"

        else:

            rating = "偏弱"


        st.metric(
            "财务质量评分",
            f"{score} / 100"
        )


        st.write(
            f"### 综合判断：{rating}"
        )


        # =====================================================
        # 5. 优势
        # =====================================================

        if positive_messages:

            st.subheader(
                "✅ 当前主要优势"
            )

            for message in positive_messages:

                st.write(
                    message
                )


        # =====================================================
        # 6. 风险
        # =====================================================

        if risk_messages:

            st.subheader(
                "⚠️ 当前主要风险"
            )

            for message in risk_messages:

                st.write(
                    message
                )


        # =====================================================
        # 7. 原始指标数据
        # =====================================================

        st.subheader(
            "📋 财务指标原始数据"
        )

        st.dataframe(
            indicators.head(10),
            use_container_width=True,
            hide_index=True
        )


    except Exception as e:

        st.error(
            "❌ 财务分析过程中出现错误"
        )

        st.code(
            str(e)
        )


st.divider()

st.caption(
    "V4：行情 + 财务指标 + 财务质量初步判断。"
    "后续将加入5年趋势、现金流/利润匹配、应收账款、存货及价值投资10步分析。"
)
