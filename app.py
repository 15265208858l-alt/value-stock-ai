import streamlit as st
import akshare as ak
import pandas as pd
import time

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("真实A股数据测试版")

st.divider()


@st.cache_data(ttl=300)
def get_stock_info(stock_code, retry=3):
    last_error = None

    for i in range(retry):
        try:
            data = ak.stock_individual_info_em(
                symbol=stock_code
            )

            if data is not None and not data.empty:
                return data

        except Exception as e:
            last_error = e
            time.sleep(2)

    raise last_error


@st.cache_data(ttl=300)
def get_stock_history(stock_code, retry=3):
    last_error = None

    for i in range(retry):
        try:
            data = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                adjust="qfq"
            )

            if data is not None and not data.empty:
                return data

        except Exception as e:
            last_error = e
            time.sleep(2)

    raise last_error


stock_code = st.text_input(
    "请输入A股股票代码",
    placeholder="例如：600089、000333、601899"
)

if st.button("获取A股数据", type="primary"):

    if not stock_code:
        st.warning("⚠️ 请先输入股票代码")
        st.stop()

    stock_code = stock_code.strip()

    st.info(f"正在获取 {stock_code} 的A股数据，请稍候...")

    # =============================
    # 1. 股票基本信息
    # =============================

    try:
        info = get_stock_info(stock_code)

        st.success("✅ 股票基本信息获取成功")

        st.subheader("📌 股票基本信息")

        if isinstance(info, pd.DataFrame):

            info.columns = ["项目", "数值"]

            st.dataframe(
                info,
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:

        st.error("❌ 股票基本信息获取失败")

        st.code(str(e))

    # =============================
    # 2. 历史行情
    # =============================

    try:

        hist = get_stock_history(stock_code)

        st.success("✅ 历史行情获取成功")

        st.subheader("📈 最近30个交易日行情")

        hist = hist.tail(30)

        st.dataframe(
            hist,
            use_container_width=True,
            hide_index=True
        )

        if "日期" in hist.columns and "收盘" in hist.columns:

            chart_data = hist.set_index("日期")["收盘"]

            st.subheader("📊 收盘价走势")

            st.line_chart(chart_data)

    except Exception as e:

        st.error("❌ 历史行情获取失败")

        st.code(str(e))
