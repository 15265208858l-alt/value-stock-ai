import streamlit as st
import akshare as ak
import pandas as pd

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("A股长期价值投资分析 V5")

st.divider()


# =========================================================
# 基础函数
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


def safe_float(value):

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


def find_column(df, candidates):

    for column in candidates:

        if column in df.columns:
            return column

    return None


def prepare_annual_data(df):

    """
    从多个报告期中尽量提取年度数据。
    优先选择每年12月附近的报告期。
    """

    data = df.copy()

    date_col = None

    candidates = [
        "日期",
        "报告期",
        "报告日期",
        "截止日期"
    ]

    for col in candidates:

        if col in data.columns:

            date_col = col
            break

    if date_col is None:

        if data.index.name in candidates:

            data = data.reset_index()

            date_col = data.columns[0]

        else:

            return data.head(5)


    data[date_col] = pd.to_datetime(
        data[date_col],
        errors="coerce"
    )

    data = data.dropna(
        subset=[date_col]
    )

    if data.empty:

        return df.head(5)


    # 优先提取年末报告
    annual = data[
        data[date_col].dt.month == 12
    ].copy()


    # 如果没有年末数据，则退回按年份去重
    if annual.empty:

        data["年份"] = data[date_col].dt.year

        annual = (
            data
            .sort_values(date_col)
            .groupby("年份")
            .tail(1)
        )

    else:

        annual["年份"] = (
            annual[date_col]
            .dt.year
        )

        annual = (
            annual
            .sort_values(date_col)
            .groupby("年份")
            .tail(1)
        )


    # 最近5个年度
    annual = (
        annual
        .sort_values(date_col)
        .tail(5)
    )

    return annual


def get_trend_status(values):

    clean = [
        x for x in values
        if x is not None
    ]

    if len(clean) < 2:

        return "数据不足"

    first = clean[0]

    last = clean[-1]

    difference = last - first

    if difference > 5:

        return "明显改善"

    elif difference > 0:

        return "改善"

    elif difference < -5:

        return "明显恶化"

    elif difference < 0:

        return "略有恶化"

    else:

        return "基本稳定"


# =========================================================
# 输入
# =========================================================

stock_code = st.text_input(
    "请输入A股股票代码",
    placeholder="例如：600089、000333、601899"
)


if st.button(
    "开始5年趋势分析",
    type="primary"
):

    if not stock_code:

        st.warning(
            "⚠️ 请先输入股票代码"
        )

        st.stop()


    stock_code = stock_code.strip()


    if len(stock_code) != 6 or not stock_code.isdigit():

        st.error(
            "❌ 股票代码必须是6位数字，例如：600089"
        )

        st.stop()


    st.info(
        f"正在分析 {stock_code} 的长期趋势，请稍候……"
    )


    # =====================================================
    # 1. 行情
    # =====================================================

    try:

        history = get_history_data(
            stock_code
        )

        if history is not None:

            latest = history.iloc[-1]

            st.success(
                "✅ 历史行情获取成功"
            )

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "最新收盘价",
                f"{float(latest['close']):.2f}"
            )

            c2.metric(
                "最新交易日",
                str(latest["date"])
            )

            c3.metric(
                "最高价",
                f"{float(latest['high']):.2f}"
            )

            c4.metric(
                "最低价",
                f"{float(latest['low']):.2f}"
            )

    except Exception as e:

        st.error(
            "❌ 历史行情获取失败"
        )

        st.code(
            str(e)
        )


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


        # =================================================
        # 3. 年度数据
        # =================================================

        annual = prepare_annual_data(
            indicators
        )


        st.subheader(
            "📅 近5年财务趋势"
        )


        # 找指标列
        roe_col = find_column(
            annual,
            [
                "加权净资产收益率(%)",
                "加权净资产收益率",
                "净资产收益率(%)",
                "净资产收益率"
            ]
        )


        revenue_col = find_column(
            annual,
            [
                "主营业务收入增长率(%)",
                "主营业务收入增长率"
            ]
        )


        profit_col = find_column(
            annual,
            [
                "净利润增长率(%)",
                "净利润增长率"
            ]
        )


        debt_col = find_column(
            annual,
            [
                "资产负债率(%)",
                "资产负债率"
            ]
        )


        # =============================================
        # 4. 构造趋势表
        # =============================================

        trend_data = {}

        year_column = None

        if "年份" in annual.columns:

            year_column = "年份"

        else:

            for candidate in [
                "日期",
                "报告期",
                "报告日期",
                "截止日期"
            ]:

                if candidate in annual.columns:

                    year_column = candidate
                    break


        if year_column is not None:

            if year_column == "年份":

                years = annual[
                    year_column
                ].astype(str)

            else:

                years = pd.to_datetime(
                    annual[year_column],
                    errors="coerce"
                ).dt.year.astype("Int64").astype(str)

        else:

            years = [
                str(i + 1)
                for i in range(len(annual))
            ]


        # ROE
        if roe_col:

            trend_data["ROE"] = [
                safe_float(x)
                for x in annual[roe_col]
            ]


        # 营收增长
        if revenue_col:

            trend_data["营收增长率"] = [
                safe_float(x)
                for x in annual[revenue_col]
            ]


        # 净利润增长
        if profit_col:

            trend_data["净利润增长率"] = [
                safe_float(x)
                for x in annual[profit_col]
            ]


        # 负债率
        if debt_col:

            trend_data["资产负债率"] = [
                safe_float(x)
                for x in annual[debt_col]
            ]


        trend_df = pd.DataFrame(
            trend_data,
            index=years
        )


        trend_df.index.name = "年份"


        st.dataframe(
            trend_df,
            use_container_width=True
        )


        # =================================================
        # 5. ROE趋势
        # =================================================

        if "ROE" in trend_df.columns:

            st.subheader(
                "📈 ROE趋势"
            )

            st.line_chart(
                trend_df["ROE"]
            )


        # =================================================
        # 6. 营收增长趋势
        # =================================================

        if "营收增长率" in trend_df.columns:

            st.subheader(
                "📈 营收增长率趋势"
            )

            st.line_chart(
                trend_df["营收增长率"]
            )


        # =================================================
        # 7. 净利润增长趋势
        # =================================================

        if "净利润增长率" in trend_df.columns:

            st.subheader(
                "📈 净利润增长率趋势"
            )

            st.line_chart(
                trend_df["净利润增长率"]
            )


        # =================================================
        # 8. 资产负债率趋势
        # =================================================

        if "资产负债率" in trend_df.columns:

            st.subheader(
                "🏦 资产负债率趋势"
            )

            st.line_chart(
                trend_df["资产负债率"]
            )


        # =================================================
        # 9. 趋势判断
        # =================================================

        st.divider()

        st.subheader(
            "🔍 长期趋势判断"
        )


        if "ROE" in trend_df.columns:

            roe_status = get_trend_status(
                trend_df["ROE"].tolist()
            )

            st.write(
                f"**ROE：** {roe_status}"
            )


        if "营收增长率" in trend_df.columns:

            revenue_status = get_trend_status(
                trend_df["营收增长率"].tolist()
            )

            st.write(
                f"**营收增长：** {revenue_status}"
            )


        if "净利润增长率" in trend_df.columns:

            profit_status = get_trend_status(
                trend_df["净利润增长率"].tolist()
            )

            st.write(
                f"**净利润增长：** {profit_status}"
            )


        if "资产负债率" in trend_df.columns:

            debt_values = trend_df[
                "资产负债率"
            ].dropna().tolist()

            if len(debt_values) >= 2:

                debt_change = (
                    debt_values[-1]
                    - debt_values[0]
                )

                if debt_change < -5:

                    debt_status = "明显下降，偿债压力改善"

                elif debt_change < 5:

                    debt_status = "总体稳定"

                else:

                    debt_status = "明显上升，需要关注杠杆"

                st.write(
                    f"**资产负债率：** {debt_status}"
                )


        # =================================================
        # 10. 初步综合判断
        # =================================================

        st.subheader(
            "🎯 V5初步判断"
        )


        positive = 0
        negative = 0


        if "ROE" in trend_df.columns:

            values = trend_df["ROE"].dropna()

            if len(values) >= 2:

                if values.iloc[-1] >= values.iloc[0]:

                    positive += 1

                else:

                    negative += 1


        if "营收增长率" in trend_df.columns:

            values = trend_df[
                "营收增长率"
            ].dropna()

            if len(values) >= 2:

                if values.iloc[-1] >= values.iloc[0]:

                    positive += 1

                else:

                    negative += 1


        if "净利润增长率" in trend_df.columns:

            values = trend_df[
                "净利润增长率"
            ].dropna()

            if len(values) >= 2:

                if values.iloc[-1] >= values.iloc[0]:

                    positive += 1

                else:

                    negative += 1


        if "资产负债率" in trend_df.columns:

            values = trend_df[
                "资产负债率"
            ].dropna()

            if len(values) >= 2:

                if values.iloc[-1] <= values.iloc[0]:

                    positive += 1

                else:

                    negative += 1


        if positive > negative:

            st.success(
                "🟢 从趋势角度看，公司经营质量总体向好。"
            )

        elif positive == negative:

            st.warning(
                "🟡 公司经营质量表现分化，需要进一步研究。"
            )

        else:

            st.error(
                "🔴 多项指标趋势走弱，需要重点排查经营风险。"
            )


    except Exception as e:

        st.error(
            "❌ 趋势分析过程中出现错误"
        )

        st.code(
            str(e)
        )


st.divider()

st.caption(
    "V5：多年度财务趋势分析。"
    "下一阶段将增加营收/净利润绝对值、经营现金流、应收账款、存货及现金流匹配度。"
)
