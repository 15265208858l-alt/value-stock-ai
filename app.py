import streamlit as st
import akshare as ak
import pandas as pd

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("A股真实行情数据测试版")

st.divider()


def get_market_code(stock_code):
    """根据股票代码判断上海/深圳市场"""
    if stock_code.startswith(("6", "68")):
        return "sh" + stock_code
    elif stock_code.startswith(("0", "3")):
        return "sz" + stock_code
    elif stock_code.startswith(("4", "8")):
        return "bj" + stock_code
    else:
        return stock_code


def get_realtime_data(stock_code):
    """优先使用新浪获取实时A股行情"""
    try:
        spot = ak.stock_zh_a_spot()

        if spot is None or spot.empty:
            return None

        result = spot[spot["代码"].astype(str) == stock_code]

        if result.empty:
            return None

        return result.iloc[0]

    except Exception as e:
        raise RuntimeError(f"新浪实时行情获取失败：{e}")


def get_history_data(stock_code):
    """使用腾讯获取历史行情"""
    market_code = get_market_code(stock_code)

    try:
        hist = ak.stock_zh_a_hist_tx(
            symbol=market_code,
            start_date="20250101",
            end_date="20500101",
            adjust=""
        )

        if hist is None or hist.empty:
            return None

        return hist

    except Exception as e:
        raise RuntimeError(f"腾讯历史行情获取失败：{e}")


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
        st.error("❌ 股票代码应输入6位数字，例如 600089")
        st.stop()

    st.info(f"正在获取 {stock_code} 的真实A股数据，请稍候……")

    # =========================
    # 1. 实时行情
    # =========================

    try:
        realtime = get_realtime_data(stock_code)

        if realtime is None:
            st.error("❌ 没有找到该股票的实时行情")
        else:
            st.success("✅ 实时A股行情获取成功")

            st.subheader("📌 最新行情")

            realtime_display = pd.DataFrame({
                "指标": [
                    "股票代码",
                    "股票名称",
                    "最新价",
                    "涨跌幅",
                    "涨跌额",
                    "今开",
                    "最高",
                    "最低",
                    "成交量",
                    "成交额"
                ],
                "数据": [
                    realtime.get("代码", "-"),
                    realtime.get("名称", "-"),
                    realtime.get("最新价", "-"),
                    realtime.get("涨跌幅", "-"),
                    realtime.get("涨跌额", "-"),
                    realtime.get("今开", "-"),
                    realtime.get("最高", "-"),
                    realtime.get("最低", "-"),
                    realtime.get("成交量", "-"),
                    realtime.get("成交额", "-")
                ]
            })

            st.dataframe(
                realtime_display,
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.error("❌ 实时行情获取失败")
        st.code(str(e))

    # =========================
    # 2. 历史行情
    # =========================

    try:
        history = get_history_data(stock_code)

        if history is None:
            st.error("❌ 没有获取到历史行情")
        else:
            st.success("✅ 腾讯历史行情获取成功")

            st.subheader("📈 最近30个交易日")

            history_30 = history.tail(30)

            st.dataframe(
                history_30,
                use_container_width=True,
                hide_index=True
            )

            # 收盘价走势图
            if "date" in history.columns and "close" in history.columns:

                chart = history_30.copy()

                chart["date"] = pd.to_datetime(chart["date"])

                chart = chart.set_index("date")

                st.subheader("📊 收盘价走势")

                st.line_chart(chart["close"])

    except Exception as e:
        st.error("❌ 历史行情获取失败")
        st.code(str(e))


st.divider()

st.caption(
    "数据来源：AKShare 可用公开数据接口。"
    "数据仅用于研究分析，不构成投资建议。"
)
