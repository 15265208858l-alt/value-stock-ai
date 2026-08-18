import streamlit as st
import akshare as ak
import pandas as pd

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("A股行情 + 财务数据测试版")

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
    """获取腾讯历史行情"""
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
    """
    获取新浪财务报表
    report_type:
    资产负债表 / 利润表 / 现金流量表
    """
    market_code = get_market_code(stock_code)

    data = ak.stock_financial_report_sina(
        stock=market_code,
        symbol=report_type
    )

    if data is None or data.empty:
        return None

    return data


stock_code = st.text_input(
    "请输入A股股票代码",
    placeholder="例如：600089、000333、601899"
)


if st.button("获取A股行情+财务数据", type="primary"):

    if not stock_code:
        st.warning("⚠️ 请先输入股票代码")
        st.stop()

    stock_code = stock_code.strip()

    if len(stock_code) != 6 or not stock_code.isdigit():
        st.error("❌ 股票代码必须是6位数字，例如：600089")
        st.stop()

    # =========================
    # 1. 历史行情
    # =========================

    st.info(f"正在获取 {stock_code} 数据，请稍候……")

    try:
        history = get_history_data(stock_code)

        if history is not None:

            st.success("✅ A股历史行情获取成功")

            latest = history.iloc[-1]

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

            st.subheader("📌 最新交易日行情")

            st.dataframe(
                latest_data,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.warning("⚠️ 没有获取到历史行情")

    except Exception as e:
        st.error("❌ 历史行情获取失败")
        st.code(str(e))


    # =========================
    # 2. 利润表
    # =========================

    try:

        profit = get_financial_report(
            stock_code,
            "利润表"
        )

        if profit is not None:

            st.success("✅ 利润表获取成功")

            st.subheader("📑 利润表")

            st.dataframe(
                profit.head(10),
                use_container_width=True,
                hide_index=True
            )

        else:
            st.warning("⚠️ 利润表没有获取到数据")

    except Exception as e:

        st.error("❌ 利润表获取失败")

        st.code(str(e))


    # =========================
    # 3. 资产负债表
    # =========================

    try:

        balance = get_financial_report(
            stock_code,
            "资产负债表"
        )

        if balance is not None:

            st.success("✅ 资产负债表获取成功")

            st.subheader("🏦 资产负债表")

            st.dataframe(
                balance.head(10),
                use_container_width=True,
                hide_index=True
            )

        else:
            st.warning("⚠️ 资产负债表没有获取到数据")

    except Exception as e:

        st.error("❌ 资产负债表获取失败")

        st.code(str(e))


    # =========================
    # 4. 现金流量表
    # =========================

    try:

        cashflow = get_financial_report(
            stock_code,
            "现金流量表"
        )

        if cashflow is not None:

            st.success("✅ 现金流量表获取成功")

            st.subheader("💰 现金流量表")

            st.dataframe(
                cashflow.head(10),
                use_container_width=True,
                hide_index=True
            )

        else:
            st.warning("⚠️ 现金流量表没有获取到数据")

    except Exception as e:

        st.error("❌ 现金流量表获取失败")

        st.code(str(e))


st.divider()

st.caption(
    "当前版本用于验证A股行情与财务数据接口。"
    "后续将自动计算ROE、增长率、现金流质量、负债率等指标。"
)
