import streamlit as st
import akshare as ak
import pandas as pd

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("A股行情 + 财务指标分析 V3")

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

    history = ak.stock_zh_a_hist_tx(
        symbol=market_code,
        start_date="20200101",
        end_date="20500101",
        adjust=""
    )

    if history is None or history.empty:
        return None

    return history


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

    """
    获取新浪财务分析指标
    """

    data = ak.stock_financial_analysis_indicator(
        stock=stock_code
    )

    if data is None or data.empty:
        return None

    return data


def safe_number(value):

    try:

        if value is None:
            return None

        text = str(value).strip()

        if text in ["", "--", "nan", "None"]:
            return None

        text = text.replace(",", "")

        return float(text)

    except Exception:

        return None


stock_code = st.text_input(
    "请输入A股股票代码",
    placeholder="例如：600089、000333、601899"
)


if st.button(
    "开始财务分析",
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


    # ==================================================
    # 1. 行情
    # ==================================================

    st.info(
        f"正在分析 {stock_code}，请稍候……"
    )


    try:

        history = get_history_data(
            stock_code
        )

        if history is not None:

            latest = history.iloc[-1]

            st.success(
                "✅ A股历史行情获取成功"
            )

            st.subheader(
                "📌 最新行情"
            )

            latest_data = pd.DataFrame({

                "指标": [

                    "股票代码",
                    "最新交易日",
                    "最新收盘价",
                    "开盘价",
                    "最高价",
                    "最低价"

                ],

                "数据": [

                    stock_code,
                    latest["date"],
                    latest["close"],
                    latest["open"],
                    latest["high"],
                    latest["low"]

                ]

            })


            st.dataframe(

                latest_data,

                use_container_width=True,

                hide_index=True

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


    # ==================================================
    # 2. 财务指标
    # ==================================================

    try:

        indicators = get_financial_indicators(
            stock_code
        )


        if indicators is None:

            st.warning(
                "⚠️ 没有获取到财务指标"
            )

        else:

            st.success(
                "✅ 财务指标获取成功"
            )


            st.subheader(
                "📊 核心财务指标"
            )


            # 如果日期存在于索引中，转换为普通列
            indicators_display = indicators.copy()

            if indicators_display.index.name is not None:

                indicators_display = (
                    indicators_display
                    .reset_index()
                )


            # 显示最新一期
            latest_financial = (
                indicators
                .iloc[0]
                .to_frame(
                    name="最新值"
                )
            )


            latest_financial.index.name = "指标"


            st.dataframe(

                latest_financial.head(60),

                use_container_width=True

            )


            # ==================================================
            # 重点指标卡片
            # ==================================================

            st.subheader(
                "⭐ 核心价值投资指标"
            )


            latest_row = indicators.iloc[0]


            def find_value(
                candidates
            ):

                for col in candidates:

                    if col in indicators.columns:

                        return safe_number(
                            latest_row[col]
                        )

                return None


            roe = find_value([
                "加权净资产收益率(%)",
                "加权净资产收益率",
                "净资产收益率(%)",
                "净资产收益率"
            ])


            gross_margin = find_value([
                "销售毛利率(%)",
                "销售毛利率"
            ])


            net_margin = find_value([
                "销售净利率(%)",
                "销售净利率"
            ])


            revenue_growth = find_value([
                "主营业务收入增长率(%)",
                "主营业务收入增长率"
            ])


            profit_growth = find_value([
                "净利润增长率(%)",
                "净利润增长率"
            ])


            operating_cashflow = find_value([
                "每股经营性现金流(元)",
                "每股经营性现金流"
            ])


            debt_ratio = find_value([
                "资产负债率(%)",
                "资产负债率"
            ])


            col1, col2, col3 = st.columns(3)


            col1.metric(
                "ROE",
                "暂无" if roe is None
                else f"{roe:.2f}%"
            )


            col2.metric(
                "销售毛利率",
                "暂无" if gross_margin is None
                else f"{gross_margin:.2f}%"
            )


            col3.metric(
                "销售净利率",
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


            st.subheader(
                "💰 每股经营现金流"
            )


            if operating_cashflow is not None:

                st.metric(
                    "每股经营现金流",
                    f"{operating_cashflow:.2f} 元"
                )

            else:

                st.info(
                    "暂无可用数据"
                )


            # ==================================================
            # 3. 财务质量初步判断
            # ==================================================

            st.subheader(
                "🔍 财务质量初步判断"
            )


            score = 0


            comments = []


            # ROE
            if roe is not None:

                if roe >= 15:

                    score += 20

                    comments.append(
                        "✅ ROE达到15%以上，盈利能力较强。"
                    )

                elif roe >= 10:

                    score += 15

                    comments.append(
                        "🟡 ROE处于中等水平。"
                    )

                else:

                    score += 8

                    comments.append(
                        "⚠️ ROE偏低，需要进一步分析盈利能力。"
                    )


            # 营收增长
            if revenue_growth is not None:

                if revenue_growth >= 10:

                    score += 20

                    comments.append(
                        "✅ 营收保持较好的增长。"
                    )

                elif revenue_growth >= 0:

                    score += 12

                    comments.append(
                        "🟡 营收保持增长，但速度一般。"
                    )

                else:

                    score += 5

                    comments.append(
                        "⚠️ 营收出现负增长。"
                    )


            # 净利润增长
            if profit_growth is not None:

                if profit_growth >= 10:

                    score += 20

                    comments.append(
                        "✅ 净利润保持较好的增长。"
                    )

                elif profit_growth >= 0:

                    score += 12

                    comments.append(
                        "🟡 净利润增长一般。"
                    )

                else:

                    score += 5

                    comments.append(
                        "⚠️ 净利润出现负增长。"
                    )


            # 负债率
            if debt_ratio is not None:

                if debt_ratio < 50:

                    score += 20

                    comments.append(
                        "✅ 资产负债率相对稳健。"
                    )

                elif debt_ratio < 70:

                    score += 12

                    comments.append(
                        "🟡 资产负债率需要持续观察。"
                    )

                else:

                    score += 5

                    comments.append(
                        "⚠️ 资产负债率偏高。"
                    )


            # 现金流
            if operating_cashflow is not None:

                if operating_cashflow > 0:

                    score += 20

                    comments.append(
                        "✅ 每股经营现金流为正。"
                    )

                else:

                    comments.append(
                        "🚨 每股经营现金流为负，需要重点排查。"
                    )


            # ==================================================
            # 综合评分
            # ==================================================

            st.subheader(
                "🎯 财务质量评分"
            )


            st.metric(
                "综合财务质量分数",
                f"{score} / 100"
            )


            for comment in comments:

                st.write(
                    comment
                )


    except Exception as e:

        st.error(
            "❌ 财务指标获取失败"
        )

        st.code(
            str(e)
        )


st.divider()


st.caption(
    "V3版本：行情 + 财务报表 + 核心财务指标。"
    "后续将增加5年趋势、应收账款、存货、现金流匹配度及价值投资10步分析。"
)
