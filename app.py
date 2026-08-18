import streamlit as st
import akshare as ak
import pandas as pd

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("A股真实行情数据系统")

st.divider()


def get_market_code(stock_code):
    """根据股票代码判断市场"""
    if stock_code.startswith(("6", "68")):
        return "sh" + stock_code
    elif stock_code.startswith(("0", "3")):
        return "sz" + stock_code
    elif stock_code.startswith(("4", "8")):
        return "bj" + stock_code
    else:
        return stock_code


def get_history_data(stock_code):
    """获取腾讯A股历史行情"""

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


stock_code = st.text_input(
    "请输入A股股票代码",
    placeholder="例如：600089、000333、601899"
)


if st.button("获取真实A股数据", type="primary"):

    if not stock_code:
        st.warning("⚠️ 请先输入股票代码")
        st.stop()

    stock_code = stock_code.strip()

    if len(stock_code) != 6 or not stock_code.isdigit():
        st.error("❌ 股票代码必须是6位数字，例如：600089")
        st.stop()

    st.info(f"正在获取 {stock_code} 的历史行情，请稍候……")

    try:

        history = get_history_data(stock_code)

        if history is None:
            st.error("❌ 没有获取到该股票的历史行情")
            st.stop()

        # =========================
        # 最新交易日数据
        # =========================

        latest = history.iloc[-1]

        st.success("✅ A股历史行情获取成功")

        st.subheader("📌 最新交易日行情")

        latest_data = pd.DataFrame({
            "指标": [
                "股票代码",
                "最新交易日",
                "最新收盘价",
                "开盘价",
                "最高价",
                "最低价",
                "成交量"
            ],
            "数据": [
                stock_code,
                latest["date"],
                latest["close"],
                latest["open"],
                latest["high"],
                latest["low"],
                latest["amount"]
            ]
        })

        st.dataframe(
            latest_data,
            use_container_width=True,
            hide_index=True
        )

        # =========================
        # 最近30个交易日
        # =========================

        st.subheader("📈 最近30个交易日")

        history_30 = history.tail(30)

        st.dataframe(
            history_30,
            use_container_width=True,
            hide_index=True
        )

        # =========================
        # 收盘价走势图
        # =========================

        st.subheader("📊 收盘价走势")

        chart_data = history.copy()

        chart_data["date"] = pd.to_datetime(
            chart_data["date"]
        )

        chart_data = chart_data.set_index("date")

        st.line_chart(
            chart_data["close"]
        )

        # =========================
        # 基础统计
        # =========================

        st.subheader("📊 基础行情分析")

        latest_close = float(latest["close"])

        recent_close = history_30["close"].astype(float)

        change_30 = (
            latest_close / float(recent_close.iloc[0]) - 1
        ) * 100

        high_30 = float(recent_close.max())
        low_30 = float(recent_close.min())

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "最新收盘价",
            f"{latest_close:.2f}"
        )

        col2.metric(
            "近30日涨跌",
            f"{change_30:.2f}%"
        )

        col3.metric(
            "近30日最高",
            f"{high_30:.2f}"
        )

        col4.metric(
            "近30日最低",
            f"{low_30:.2f}"
        )

        st.info(
            "当前版本先采用稳定的历史行情数据。"
            "下一阶段将继续接入财务数据和价值投资分析模型。"
        )

    except Exception as e:

        st.error("❌ A股数据获取失败")

        st.code(str(e))
