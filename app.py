import streamlit as st
import akshare as ak
import pandas as pd

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("真实A股数据测试版")

st.divider()

stock_code = st.text_input(
    "请输入A股股票代码",
    placeholder="例如：600089、000333、601899"
)

if st.button("获取A股数据", type="primary"):

    if not stock_code:
        st.warning("⚠️ 请先输入股票代码")
        st.stop()

    stock_code = stock_code.strip()

    try:
        # 获取股票基本信息
        info = ak.stock_individual_info_em(
            symbol=stock_code
        )

        st.success(f"✅ 成功获取 {stock_code} 的股票数据")

        st.subheader("📌 股票基本信息")

        if isinstance(info, pd.DataFrame):

            info.columns = ["项目", "数值"]

            st.dataframe(
                info,
                use_container_width=True,
                hide_index=True
            )

        # 获取历史行情
        st.subheader("📈 最近30个交易日行情")

        hist = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            adjust="qfq"
        )

        if isinstance(hist, pd.DataFrame) and not hist.empty:

            hist = hist.tail(30)

            st.dataframe(
                hist,
                use_container_width=True,
                hide_index=True
            )

            # 收盘价走势图
            chart_data = hist.set_index("日期")["收盘"]

            st.line_chart(chart_data)

        else:
            st.warning("⚠️ 暂时没有获取到历史行情数据")

    except Exception as e:

        st.error("❌ 获取A股数据失败")

        st.write("错误信息：")
        st.code(str(e))
