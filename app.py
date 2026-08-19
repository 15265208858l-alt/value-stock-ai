import streamlit as st
import akshare as ak
import pandas as pd
import math


# =========================================================
# 0. 页面设置
# =========================================================

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("A股长期价值投资分析系统 V12.2")
st.caption(
    "稳定数据链路版：行情 + 财务指标 + 三大报表 + "
    "5年质量 + 财务排雷 + PE/PB估值 + 投资价格区间"
)

st.divider()


# =========================================================
# 1. 基础函数
# =========================================================

def safe_float(value):
    """安全转换数字"""

    try:
        if value is None:
            return None

        if isinstance(value, float) and math.isnan(value):
            return None

        text = str(value).strip()

        if text in [
            "",
            "--",
            "None",
            "none",
            "NaN",
            "nan",
            "null"
        ]:
            return None

        text = text.replace(",", "")
        text = text.replace("%", "")

        return float(text)

    except Exception:
        return None


def clean_stock_code(code):
    """检查股票代码"""

    if code is None:
        return ""

    code = str(code).strip()

    if len(code) != 6:
        return ""

    if not code.isdigit():
        return ""

    return code


def get_market_code(stock_code):
    """上海/深圳/北京市场代码"""

    if stock_code.startswith(("6", "68")):
        return "sh" + stock_code

    if stock_code.startswith(("0", "3")):
        return "sz" + stock_code

    if stock_code.startswith(("4", "8")):
        return "bj" + stock_code

    return stock_code


def get_symbol_code(stock_code):
    """AKShare部分接口使用的市场代码"""

    if stock_code.startswith(("6", "68")):
        return "SH" + stock_code

    if stock_code.startswith(("0", "3")):
        return "SZ" + stock_code

    if stock_code.startswith(("4", "8")):
        return "BJ" + stock_code

    return stock_code


def find_column(df, candidates):
    """从DataFrame中寻找字段"""

    if df is None or df.empty:
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


def format_money(value):
    """金额转亿元显示"""

    if value is None:
        return "暂无"

    try:
        return f"{value / 1e8:.2f} 亿元"
    except Exception:
        return "暂无"


def parse_date_column(df):
    """寻找并解析日期字段"""

    if df is None or df.empty:
        return df, None

    date_col = find_column(
        df,
        [
            "日期",
            "报告期",
            "报告日期",
            "截止日期",
            "REPORT_DATE"
        ]
    )

    if date_col is None:
        return df.copy(), None

    result = df.copy()

    result["_分析日期"] = pd.to_datetime(
        result[date_col],
        errors="coerce"
    )

    result = result.dropna(
        subset=["_分析日期"]
    )

    if result.empty:
        return df.copy(), date_col

    result = (
        result
        .sort_values(
            "_分析日期",
            ascending=False
        )
        .reset_index(drop=True)
    )

    return result, date_col


# =========================================================
# 2. 实时行情
# =========================================================

@st.cache_data(ttl=60)
def get_realtime_market(stock_code):

    try:

        df = ak.stock_zh_a_spot_em()

        if df is None or df.empty:
            return None

        code_col = find_column(
            df,
            ["代码", "股票代码"]
        )

        if code_col is None:
            return None

        result = df[
            df[code_col].astype(str)
            == stock_code
        ]

        if result.empty:
            return None

        return result.iloc[0].to_dict()

    except Exception:

        return None


# =========================================================
# 3. 历史行情
# =========================================================

@st.cache_data(ttl=300)
def get_history_data(stock_code):

    # 第一数据源
    try:

        data = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date="20200101",
            end_date="20500101",
            adjust=""
        )

        if data is not None and not data.empty:
            return data

    except Exception:
        pass

    # 备用：腾讯
    try:

        data = ak.stock_zh_a_hist_tx(
            symbol=get_market_code(stock_code),
            start_date="20200101",
            end_date="20500101",
            adjust=""
        )

        if data is not None and not data.empty:
            return data

    except Exception:
        pass

    return None


def get_history_latest_price(history):

    if history is None or history.empty:
        return None

    # 东方财富格式
    if "收盘" in history.columns:
        return safe_float(
            history.iloc[-1]["收盘"]
        )

    # 腾讯格式
    if "close" in history.columns:
        return safe_float(
            history.iloc[-1]["close"]
        )

    return None


# =========================================================
# 4. 财务指标
# =========================================================

@st.cache_data(ttl=3600)
def get_financial_indicators(stock_code):

    symbols = [
        stock_code,
        get_symbol_code(stock_code)
    ]

    # 已验证接口
    for symbol in symbols:

        try:

            data = ak.stock_financial_analysis_indicator(
                symbol=symbol
            )

            if data is not None and not data.empty:
                return data, "stock_financial_analysis_indicator"

        except Exception:
            pass

    # 备用接口
    try:

        data = ak.stock_financial_analysis_indicator_em(
            symbol=stock_code,
            indicator="按报告期"
        )

        if data is not None and not data.empty:
            return data, "stock_financial_analysis_indicator_em"

    except Exception:
        pass

    return None, None


# =========================================================
# 5. 三张财务报表
# =========================================================

@st.cache_data(ttl=3600)
def get_financial_report(
    stock_code,
    report_type
):

    market_code = get_market_code(
        stock_code
    )

    try:

        data = ak.stock_financial_report_sina(
            stock=market_code,
            symbol=report_type
        )

        if data is not None and not data.empty:
            return data

    except Exception:
        pass

    return None


# =========================================================
# 6. 财务指标字段
# =========================================================

def get_indicator_columns(df):

    return {

        "roe": find_column(
            df,
            [
                "加权净资产收益率(%)",
                "加权净资产收益率",
                "摊薄净资产收益率(%)",
                "摊薄净资产收益率",
                "净资产收益率(%)",
                "净资产收益率",
                "ROEJQ"
            ]
        ),

        "revenue_growth": find_column(
            df,
            [
                "主营业务收入增长率(%)",
                "主营业务收入增长率",
                "营业收入增长率(%)",
                "营业收入增长率",
                "TOTALOPERATEREVETZ"
            ]
        ),

        "profit_growth": find_column(
            df,
            [
                "净利润增长率(%)",
                "净利润增长率",
                "归属净利润同比增长(%)",
                "PARENTNETPROFITTZ"
            ]
        ),

        "debt": find_column(
            df,
            [
                "资产负债率(%)",
                "资产负债率",
                "ZCFZL"
            ]
        ),

        "eps": find_column(
            df,
            [
                "摊薄每股收益(元)",
                "摊薄每股收益",
                "基本每股收益(元)",
                "基本每股收益",
                "每股收益(元)",
                "每股收益",
                "EPSJB"
            ]
        ),

        "bvps": find_column(
            df,
            [
                "每股净资产(元)",
                "每股净资产",
                "每股净资产_调整后(元)",
                "归属母公司股东的每股净资产",
                "BPS"
            ]
        )
    }


# =========================================================
# 7. 财务指标处理
# =========================================================

def process_financial_indicators(
    indicators
):

    result = {

        "latest": {},
        "annual": {},
        "trend": pd.DataFrame()
    }

    if indicators is None or indicators.empty:
        return result

    df, date_col = parse_date_column(
        indicators
    )

    if df is None or df.empty:
        return result

    cols = get_indicator_columns(df)

    # 最新报告期
    latest = df.iloc[0]

    result["latest"] = {

        "roe": (
            safe_float(latest[cols["roe"]])
            if cols["roe"]
            else None
        ),

        "revenue_growth": (
            safe_float(
                latest[cols["revenue_growth"]]
            )
            if cols["revenue_growth"]
            else None
        ),

        "profit_growth": (
            safe_float(
                latest[cols["profit_growth"]]
            )
            if cols["profit_growth"]
            else None
        ),

        "debt": (
            safe_float(latest[cols["debt"]])
            if cols["debt"]
            else None
        ),

        "eps": (
            safe_float(latest[cols["eps"]])
            if cols["eps"]
            else None
        ),

        "bvps": (
            safe_float(latest[cols["bvps"]])
            if cols["bvps"]
            else None
        ),

        "period": (
            str(latest[date_col])
            if date_col
            else "最新报告期"
        )
    }

    # 年度数据
    annual_df = pd.DataFrame()

    if "_分析日期" in df.columns:

        annual_df = df[
            df["_分析日期"].dt.month == 12
        ].copy()

    if annual_df.empty and date_col:

        text = df[date_col].astype(str)

        mask = (
            text.str.contains(
                "12-31",
                na=False
            )
            |
            text.str.contains(
                "12/31",
                na=False
            )
            |
            text.str.contains(
                "12月31",
                na=False
            )
        )

        annual_df = df[mask].copy()

    if annual_df.empty:

        annual = latest

    else:

        annual = (
            annual_df
            .sort_values(
                "_分析日期"
            )
            .iloc[-1]
        )

    result["annual"] = {

        "roe": (
            safe_float(annual[cols["roe"]])
            if cols["roe"]
            else None
        ),

        "revenue_growth": (
            safe_float(
                annual[cols["revenue_growth"]]
            )
            if cols["revenue_growth"]
            else None
        ),

        "profit_growth": (
            safe_float(
                annual[cols["profit_growth"]]
            )
            if cols["profit_growth"]
            else None
        ),

        "debt": (
            safe_float(annual[cols["debt"]])
            if cols["debt"]
            else None
        ),

        "eps": (
            safe_float(annual[cols["eps"]])
            if cols["eps"]
            else None
        ),

        "bvps": (
            safe_float(annual[cols["bvps"]])
            if cols["bvps"]
            else None
        ),

        "period": (
            str(annual[date_col])
            if date_col
            else "年度数据"
        )
    }

    # 5年趋势
    trend = df.copy()

    if "_分析日期" in trend.columns:

        trend["年份"] = (
            trend["_分析日期"].dt.year
        )

        annual_trend = trend[
            trend["_分析日期"].dt.month == 12
        ].copy()

        if not annual_trend.empty:

            trend = (
                annual_trend
                .sort_values("_分析日期")
                .groupby("年份")
                .tail(1)
                .tail(5)
            )

        else:

            trend = (
                trend
                .sort_values("_分析日期")
                .tail(5)
            )

    rename_map = {}

    if date_col:
        rename_map[date_col] = "报告期"

    if cols["roe"]:
        rename_map[cols["roe"]] = "ROE"

    if cols["revenue_growth"]:
        rename_map[
            cols["revenue_growth"]
        ] = "营收增长率"

    if cols["profit_growth"]:
        rename_map[
            cols["profit_growth"]
        ] = "净利润增长率"

    if cols["debt"]:
        rename_map[
            cols["debt"]
        ] = "资产负债率"

    if cols["eps"]:
        rename_map[
            cols["eps"]
        ] = "EPS"

    trend = trend.rename(
        columns=rename_map
    )

    display_columns = []

    for col in [
        "报告期",
        "ROE",
        "营收增长率",
        "净利润增长率",
        "资产负债率",
        "EPS"
    ]:

        if col in trend.columns:
            display_columns.append(col)

    if display_columns:

        result["trend"] = trend[
            display_columns
        ].copy()

    return result


# =========================================================
# 8. 三张报表关键字段
# =========================================================

def get_latest_report_value(
    df,
    candidates
):

    if df is None or df.empty:
        return None

    temp, _ = parse_date_column(
        df
    )

    if temp is None or temp.empty:
        return None

    col = find_column(
        temp,
        candidates
    )

    if col is None:
        return None

    return safe_float(
        temp.iloc[0][col]
    )


def get_report_metrics(
    profit,
    balance,
    cashflow
):

    return {

        "revenue": get_latest_report_value(
            profit,
            [
                "营业总收入",
                "营业收入",
                "一、营业总收入"
            ]
        ),

        "net_profit": get_latest_report_value(
            profit,
            [
                "归属于母公司所有者的净利润",
                "归属于母公司股东的净利润",
                "净利润",
                "五、净利润"
            ]
        ),

        "receivable": get_latest_report_value(
            balance,
            [
                "应收账款",
                "应收款项"
            ]
        ),

        "inventory": get_latest_report_value(
            balance,
            [
                "存货"
            ]
        ),

        "operating_cashflow": get_latest_report_value(
            cashflow,
            [
                "经营活动产生的现金流量净额",
                "经营活动现金流量净额"
            ]
        )
    }


# =========================================================
# 9. 主界面输入
# =========================================================

stock_input = st.text_input(
    "请输入A股股票代码",
    placeholder="例如：000333、600089、601899"
)

analyze = st.button(
    "🚀 开始价值投资分析",
    type="primary"
)


# =========================================================
# 10. 开始分析
# =========================================================

if analyze:

    stock_code = clean_stock_code(
        stock_input
    )

    if not stock_code:

        st.error(
            "❌ 请输入6位数字股票代码"
        )

        st.stop()

    st.info(
        f"正在分析 {stock_code}，请稍候……"
    )

    # =====================================================
    # 一、实时行情
    # =====================================================

    st.header("📌 一、实时行情")

    market_data = get_realtime_market(
        stock_code
    )

    stock_name = stock_code
    current_price = None
    day_change = None
    realtime_pe = None
    realtime_pb = None

    if market_data:

        stock_name = market_data.get(
            "名称",
            stock_code
        )

        current_price = safe_float(
            market_data.get("最新价")
        )

        day_change = safe_float(
            market_data.get("涨跌幅")
        )

        realtime_pe = safe_float(
            market_data.get("市盈率-动态")
        )

        realtime_pb = safe_float(
            market_data.get("市净率")
        )

    # 实时价格失败，历史价格兜底
    history = get_history_data(
        stock_code
    )

    if current_price is None:

        fallback_price = (
            get_history_latest_price(
                history
            )
        )

        if fallback_price is not None:

            current_price = fallback_price

            st.warning(
                "⚠️ 实时价格接口不可用，"
                "当前价格采用最近交易日收盘价作为估值参考价。"
            )

    if current_price is not None:

        st.success(
            "✅ 当前价格获取成功"
        )

    else:

        st.error(
            "❌ 当前价格暂时无法获取"
        )

    a1, a2, a3, a4 = st.columns(4)

    a1.metric(
        "股票名称",
        str(stock_name)
    )

    a2.metric(
        "当前参考价格",
        "暂无"
        if current_price is None
        else f"{current_price:.2f} 元"
    )

    a3.metric(
        "当日涨跌幅",
        "暂无"
        if day_change is None
        else f"{day_change:.2f}%"
    )

    a4.metric(
        "动态PE",
        "暂无"
        if realtime_pe is None
        else f"{realtime_pe:.2f} 倍"
    )

    # =====================================================
    # 二、历史行情
    # =====================================================

    st.header("📈 二、历史行情")

    if history is not None:

        st.success(
            "✅ 历史行情获取成功"
        )

        with st.expander(
            "查看最近10个交易日"
        ):

            st.dataframe(
                history.tail(10),
                use_container_width=True,
                hide_index=True
            )

    else:

        st.warning(
            "⚠️ 历史行情获取失败"
        )

    # =====================================================
    # 三、财务指标
    # =====================================================

    st.header("📊 三、财务指标")

    indicators, indicator_source = (
        get_financial_indicators(
            stock_code
        )
    )

    if indicators is None:

        st.error(
            "❌ 财务指标获取失败"
        )

        st.stop()

    st.success(
        f"✅ 财务指标获取成功：{indicator_source}"
    )

    financial_data = (
        process_financial_indicators(
            indicators
        )
    )

    latest_data = financial_data[
        "latest"
    ]

    annual_data = financial_data[
        "annual"
    ]

    trend = financial_data[
        "trend"
    ]

    latest_roe = latest_data.get(
        "roe"
    )

    latest_revenue_growth = latest_data.get(
        "revenue_growth"
    )

    latest_profit_growth = latest_data.get(
        "profit_growth"
    )

    latest_debt_ratio = latest_data.get(
        "debt"
    )

    annual_roe = annual_data.get(
        "roe"
    )

    annual_revenue_growth = annual_data.get(
        "revenue_growth"
    )

    annual_profit_growth = annual_data.get(
        "profit_growth"
    )

    annual_debt_ratio = annual_data.get(
        "debt"
    )

    annual_eps = annual_data.get(
        "eps"
    )

    annual_bvps = annual_data.get(
        "bvps"
    )

    b1, b2, b3, b4 = st.columns(4)

    b1.metric(
        "最新ROE",
        "暂无"
        if latest_roe is None
        else f"{latest_roe:.2f}%"
    )

    b2.metric(
        "最新营收增长",
        "暂无"
        if latest_revenue_growth is None
        else f"{latest_revenue_growth:.2f}%"
    )

    b3.metric(
        "最新净利润增长",
        "暂无"
        if latest_profit_growth is None
        else f"{latest_profit_growth:.2f}%"
    )

    b4.metric(
        "最新负债率",
        "暂无"
        if latest_debt_ratio is None
        else f"{latest_debt_ratio:.2f}%"
    )

    st.subheader(
        "🟢 最近完整年度：长期价值投资口径"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "年度ROE",
        "暂无"
        if annual_roe is None
        else f"{annual_roe:.2f}%"
    )

    c2.metric(
        "年度EPS",
        "暂无"
        if annual_eps is None
        else f"{annual_eps:.2f} 元"
    )

    c3.metric(
        "年度营收增长",
        "暂无"
        if annual_revenue_growth is None
        else f"{annual_revenue_growth:.2f}%"
    )

    c4.metric(
        "年度净利润增长",
        "暂无"
        if annual_profit_growth is None
        else f"{annual_profit_growth:.2f}%"
    )

    c5, c6 = st.columns(2)

    c5.metric(
        "年度资产负债率",
        "暂无"
        if annual_debt_ratio is None
        else f"{annual_debt_ratio:.2f}%"
    )

    c6.metric(
        "年度每股净资产",
        "暂无"
        if annual_bvps is None
        else f"{annual_bvps:.2f} 元"
    )

    # =====================================================
    # 四、三张报表
    # =====================================================

    st.header("💰 四、三张财务报表")

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

    report_metrics = get_report_metrics(
        profit,
        balance,
        cashflow
    )

    latest_revenue = report_metrics[
        "revenue"
    ]

    latest_profit = report_metrics[
        "net_profit"
    ]

    latest_receivable = report_metrics[
        "receivable"
    ]

    latest_inventory = report_metrics[
        "inventory"
    ]

    latest_cashflow = report_metrics[
        "operating_cashflow"
    ]

    report_count = sum(
        [
            profit is not None,
            balance is not None,
            cashflow is not None
        ]
    )

    st.write(
        f"财务报表获取情况：{report_count}/3"
    )

    with st.expander(
        "查看原始财务报表"
    ):

        if profit is not None:

            st.write("### 利润表")

            st.dataframe(
                profit.head(15),
                use_container_width=True,
                hide_index=True
            )

        if balance is not None:

            st.write("### 资产负债表")

            st.dataframe(
                balance.head(15),
                use_container_width=True,
                hide_index=True
            )

        if cashflow is not None:

            st.write("### 现金流量表")

            st.dataframe(
                cashflow.head(15),
                use_container_width=True,
                hide_index=True
            )

    # =====================================================
    # 五、关键数据
    # =====================================================

    st.header("💵 五、最近一期关键数据")

    d1, d2, d3, d4, d5 = st.columns(5)

    d1.metric(
        "营业收入",
        format_money(latest_revenue)
    )

    d2.metric(
        "净利润",
        format_money(latest_profit)
    )

    d3.metric(
        "经营现金流",
        format_money(latest_cashflow)
    )

    d4.metric(
        "应收账款",
        format_money(latest_receivable)
    )

    d5.metric(
        "存货",
        format_money(latest_inventory)
    )

    # =====================================================
    # 六、财务排雷
    # =====================================================

    st.header("🚨 六、财务排雷")

    cash_profit_ratio = safe_ratio(
        latest_cashflow,
        latest_profit
    )

    receivable_ratio = safe_ratio(
        latest_receivable,
        latest_revenue
    )

    inventory_ratio = safe_ratio(
        latest_inventory,
        latest_revenue
    )

    f1, f2, f3 = st.columns(3)

    f1.metric(
        "经营现金流 / 净利润",
        "暂无"
        if cash_profit_ratio is None
        else f"{cash_profit_ratio:.2f}"
    )

    f2.metric(
        "应收账款 / 营收",
        "暂无"
        if receivable_ratio is None
        else f"{receivable_ratio:.2%}"
    )

    f3.metric(
        "存货 / 营收",
        "暂无"
        if inventory_ratio is None
        else f"{inventory_ratio:.2%}"
    )

    risk_score = 0
    risk_items = []

    if (
        cash_profit_ratio is not None
        and cash_profit_ratio < 0.7
    ):

        risk_score += 2

        risk_items.append(
            "经营现金流与净利润匹配度偏低"
        )

    if (
        receivable_ratio is not None
        and receivable_ratio > 0.40
    ):

        risk_score += 2

        risk_items.append(
            "应收账款占营业收入比例较高"
        )

    if (
        inventory_ratio is not None
        and inventory_ratio > 0.50
    ):

        risk_score += 2

        risk_items.append(
            "存货占营业收入比例较高"
        )

    if (
        annual_roe is not None
        and annual_roe < 10
    ):

        risk_score += 1

        risk_items.append(
            "长期ROE偏低"
        )

    if (
        annual_debt_ratio is not None
        and annual_debt_ratio >= 70
    ):

        risk_score += 2

        risk_items.append(
            "资产负债率偏高"
        )

    if risk_score == 0:

        st.success(
            "🟢 暂未发现明显一级财务风险"
        )

    elif risk_score <= 2:

        st.warning(
            "🟡 存在少量需要观察的风险信号"
        )

    elif risk_score <= 4:

        st.warning(
            "🟠 存在多个需要深入研究的风险信号"
        )

    else:

        st.error(
            "🔴 财务风险信号较多"
        )

    if risk_items:

        st.write(
            "### 重点风险"
        )

        for item in risk_items:

            st.write(
                f"- {item}"
            )

    # =====================================================
    # 七、5年财务质量
    # =====================================================

    st.header("⭐ 七、5年财务质量")

    if trend is not None and not trend.empty:

        st.dataframe(
            trend,
            use_container_width=True,
            hide_index=True
        )

    roe_values = []
    revenue_values = []
    profit_values = []
    debt_values = []

    if trend is not None and not trend.empty:

        if "ROE" in trend.columns:

            for value in trend["ROE"]:

                number = safe_float(value)

                if number is not None:
                    roe_values.append(number)

        if "营收增长率" in trend.columns:

            for value in trend["营收增长率"]:

                number = safe_float(value)

                if number is not None:
                    revenue_values.append(number)

        if "净利润增长率" in trend.columns:

            for value in trend["净利润增长率"]:

                number = safe_float(value)

                if number is not None:
                    profit_values.append(number)

        if "资产负债率" in trend.columns:

            for value in trend["资产负债率"]:

                number = safe_float(value)

                if number is not None:
                    debt_values.append(number)

    roe_score = 0
    growth_score = 0
    profit_score = 0
    debt_score = 0
    cash_score = 0

    # ROE 20分
    if roe_values:

        avg_roe = sum(roe_values) / len(
            roe_values
        )

        min_roe = min(roe_values)

        if avg_roe >= 20 and min_roe >= 15:

            roe_score = 20

        elif avg_roe >= 15 and min_roe >= 10:

            roe_score = 17

        elif avg_roe >= 10:

            roe_score = 13

        elif avg_roe >= 5:

            roe_score = 8

        else:

            roe_score = 3

    # 营收成长 20分
    if revenue_values:

        avg_growth = (
            sum(revenue_values)
            / len(revenue_values)
        )

        positive_years = sum(
            1
            for x in revenue_values
            if x >= 0
        )

        if (
            avg_growth >= 15
            and positive_years >= 4
        ):

            growth_score = 20

        elif (
            avg_growth >= 8
            and positive_years >= 4
        ):

            growth_score = 16

        elif avg_growth >= 0:

            growth_score = 11

        else:

            growth_score = 4

    # 净利润成长 20分
    if profit_values:

        avg_profit_growth = (
            sum(profit_values)
            / len(profit_values)
        )

        positive_profit_years = sum(
            1
            for x in profit_values
            if x >= 0
        )

        if (
            avg_profit_growth >= 20
            and positive_profit_years >= 4
        ):

            profit_score = 20

        elif (
            avg_profit_growth >= 10
            and positive_profit_years >= 4
        ):

            profit_score = 16

        elif avg_profit_growth >= 0:

            profit_score = 11

        else:

            profit_score = 4

    # 财务安全 20分
    if debt_values:

        avg_debt = (
            sum(debt_values)
            / len(debt_values)
        )

        if avg_debt < 50:

            debt_score = 20

        elif avg_debt < 60:

            debt_score = 17

        elif avg_debt < 70:

            debt_score = 13

        elif avg_debt < 80:

            debt_score = 8

        else:

            debt_score = 3

    # 现金流 20分
    if cash_profit_ratio is not None:

        if cash_profit_ratio >= 1:

            cash_score = 20

        elif cash_profit_ratio >= 0.7:

            cash_score = 16

        elif cash_profit_ratio >= 0:

            cash_score = 10

        else:

            cash_score = 3

    financial_quality_score = min(
        100,
        (
            roe_score
            + growth_score
            + profit_score
            + debt_score
            + cash_score
        )
    )

    if financial_quality_score >= 85:

        financial_rating = "优秀"

    elif financial_quality_score >= 75:

        financial_rating = "良好"

    elif financial_quality_score >= 60:

        financial_rating = "一般"

    else:

        financial_rating = "偏弱"

    q1, q2 = st.columns(2)

    q1.metric(
        "财务质量总分",
        f"{financial_quality_score}/100"
    )

    q2.metric(
        "财务质量评级",
        financial_rating
    )

    score_df = pd.DataFrame({
        "维度": [
            "ROE及盈利能力",
            "营收成长",
            "净利润成长",
            "财务安全",
            "现金流质量"
        ],
        "得分": [
            f"{roe_score}/20",
            f"{growth_score}/20",
            f"{profit_score}/20",
            f"{debt_score}/20",
            f"{cash_score}/20"
        ]
    })

    st.dataframe(
        score_df,
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # 八、价值估值
    # =====================================================

    st.header("💰 八、长期价值估值")

    st.caption(
        "长期估值优先采用最近完整年度EPS、BPS和ROE。"
    )

    valuation_eps = annual_eps
    valuation_bvps = annual_bvps
    valuation_roe = annual_roe

    v1, v2, v3, v4 = st.columns(4)

    v1.metric(
        "当前价格",
        "暂无"
        if current_price is None
        else f"{current_price:.2f} 元"
    )

    v2.metric(
        "年度EPS",
        "暂无"
        if valuation_eps is None
        else f"{valuation_eps:.2f} 元"
    )

    v3.metric(
        "年度ROE",
        "暂无"
        if valuation_roe is None
        else f"{valuation_roe:.2f}%"
    )

    v4.metric(
        "年度BPS",
        "暂无"
        if valuation_bvps is None
        else f"{valuation_bvps:.2f} 元"
    )

    current_pe = None
    current_pb = None

    if (
        current_price is not None
        and valuation_eps is not None
        and valuation_eps > 0
    ):

        current_pe = (
            current_price
            / valuation_eps
        )

    if (
        current_price is not None
        and valuation_bvps is not None
        and valuation_bvps > 0
    ):

        current_pb = (
            current_price
            / valuation_bvps
        )

    ev1, ev2 = st.columns(2)

    ev1.metric(
        "当前PE",
        "暂无"
        if current_pe is None
        else f"{current_pe:.2f} 倍"
    )

    ev2.metric(
        "当前PB",
        "暂无"
        if current_pb is None
        else f"{current_pb:.2f} 倍"
    )

    # =====================================================
    # 九、PE/PB参数
    # =====================================================

    st.subheader(
        "⚙️ 三情景估值参数"
    )

    if valuation_roe is not None:

        if valuation_roe >= 20:

            pe_conservative = 14.0
            pe_normal = 18.0
            pe_optimistic = 22.0

        elif valuation_roe >= 15:

            pe_conservative = 13.0
            pe_normal = 17.0
            pe_optimistic = 21.0

        elif valuation_roe >= 10:

            pe_conservative = 10.0
            pe_normal = 14.0
            pe_optimistic = 18.0

        else:

            pe_conservative = 8.0
            pe_normal = 11.0
            pe_optimistic = 14.0

    else:

        pe_conservative = 10.0
        pe_normal = 14.0
        pe_optimistic = 18.0

    pe1, pe2, pe3 = st.columns(3)

    pe_c = pe1.number_input(
        "保守PE",
        min_value=3.0,
        max_value=50.0,
        value=pe_conservative,
        step=1.0
    )

    pe_n = pe2.number_input(
        "中性PE",
        min_value=3.0,
        max_value=50.0,
        value=pe_normal,
        step=1.0
    )

    pe_o = pe3.number_input(
        "乐观PE",
        min_value=3.0,
        max_value=50.0,
        value=pe_optimistic,
        step=1.0
    )

    pb1, pb2, pb3 = st.columns(3)

    pb_c = pb1.number_input(
        "保守PB",
        min_value=0.3,
        max_value=10.0,
        value=1.5,
        step=0.1
    )

    pb_n = pb2.number_input(
        "中性PB",
        min_value=0.3,
        max_value=10.0,
        value=2.0,
        step=0.1
    )

    pb_o = pb3.number_input(
        "乐观PB",
        min_value=0.3,
        max_value=10.0,
        value=2.5,
        step=0.1
    )

    # =====================================================
    # 十、情景估值
    # =====================================================

    pe_c_value = None
    pe_n_value = None
    pe_o_value = None

    if (
        valuation_eps is not None
        and valuation_eps > 0
    ):

        pe_c_value = valuation_eps * pe_c
        pe_n_value = valuation_eps * pe_n
        pe_o_value = valuation_eps * pe_o

    pb_c_value = None
    pb_n_value = None
    pb_o_value = None

    if (
        valuation_bvps is not None
        and valuation_bvps > 0
    ):

        pb_c_value = valuation_bvps * pb_c
        pb_n_value = valuation_bvps * pb_n
        pb_o_value = valuation_bvps * pb_o

    if valuation_roe is not None:

        if valuation_roe >= 20:

            pe_weight = 0.75
            pb_weight = 0.25

        elif valuation_roe >= 15:

            pe_weight = 0.70
            pb_weight = 0.30

        elif valuation_roe >= 10:

            pe_weight = 0.60
            pb_weight = 0.40

        else:

            pe_weight = 0.50
            pb_weight = 0.50

    else:

        pe_weight = 0.60
        pb_weight = 0.40

    def combine_value(
        pe_value,
        pb_value
    ):

        if (
            pe_value is not None
            and pb_value is not None
        ):

            return (
                pe_value * pe_weight
                + pb_value * pb_weight
            )

        if pe_value is not None:
            return pe_value

        if pb_value is not None:
            return pb_value

        return None

    conservative_value = combine_value(
        pe_c_value,
        pb_c_value
    )

    normal_value = combine_value(
        pe_n_value,
        pb_n_value
    )

    optimistic_value = combine_value(
        pe_o_value,
        pb_o_value
    )

    st.write(
        f"估值权重：PE {pe_weight:.0%} / "
        f"PB {pb_weight:.0%}"
    )

    valuation_table = pd.DataFrame({

        "情景": [
            "保守",
            "中性",
            "乐观"
        ],

        "PE估值": [
            pe_c_value,
            pe_n_value,
            pe_o_value
        ],

        "PB估值": [
            pb_c_value,
            pb_n_value,
            pb_o_value
        ],

        "综合估值": [
            conservative_value,
            normal_value,
            optimistic_value
        ]
    })

    for col in [
        "PE估值",
        "PB估值",
        "综合估值"
    ]:

        valuation_table[col] = (
            valuation_table[col]
            .apply(
                lambda x:
                "暂无"
                if x is None
                else f"{x:.2f} 元"
            )
        )

    st.dataframe(
        valuation_table,
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # 十一、投资价格区间
    # =====================================================

    st.header(
        "💰 十一、投资价格区间"
    )

    heavy_price = None
    entry_price = None
    high_price = None

    if normal_value is not None:

        heavy_price = (
            normal_value * 0.70
        )

        entry_price = (
            normal_value * 0.85
        )

    if optimistic_value is not None:

        high_price = optimistic_value

    p1, p2, p3, p4 = st.columns(4)

    p1.metric(
        "重仓参考价",
        "暂无"
        if heavy_price is None
        else f"{heavy_price:.2f} 元"
    )

    p2.metric(
        "建仓参考价",
        "暂无"
        if entry_price is None
        else f"{entry_price:.2f} 元"
    )

    p3.metric(
        "中性合理价",
        "暂无"
        if normal_value is None
        else f"{normal_value:.2f} 元"
    )

    p4.metric(
        "高估参考价",
        "暂无"
        if high_price is None
        else f"{high_price:.2f} 元"
    )

    # =====================================================
    # 十二、价格判断
    # =====================================================

    st.subheader(
        "🔍 当前价格判断"
    )

    valuation_gap = None

    if (
        current_price is not None
        and normal_value is not None
        and normal_value > 0
    ):

        valuation_gap = (
            normal_value
            / current_price
            - 1
        ) * 100

        st.metric(
            "相对中性合理价值空间",
            f"{valuation_gap:.2f}%"
        )

        if (
            heavy_price is not None
            and current_price <= heavy_price
        ):

            st.success(
                "🟢 当前进入重仓观察区"
            )

        elif (
            entry_price is not None
            and current_price <= entry_price
        ):

            st.success(
                "🟢 当前进入建仓观察区"
            )

        elif current_price <= normal_value:

            st.info(
                "🟡 当前低于中性合理价值，但安全边际一般"
            )

        elif (
            high_price is not None
            and current_price <= high_price
        ):

            st.warning(
                "🟠 当前高于中性合理价，建议等待更好的安全边际"
            )

        else:

            st.error(
                "🔴 当前价格高于乐观估值"
            )

    else:

        st.warning(
            "⚠️ 当前数据不足，无法完成价格判断"
        )

    # =====================================================
    # 十三、综合投资评分
    # =====================================================

    st.header(
        "🏆 十三、ValueStock AI综合投资评级"
    )

    financial_component = (
        financial_quality_score * 0.30
    )

    # 成长性
    growth_component = 0

    if (
        annual_revenue_growth is not None
        and annual_profit_growth is not None
    ):

        growth_avg = (
            annual_revenue_growth
            + annual_profit_growth
        ) / 2

        if growth_avg >= 20:

            growth_component = 20

        elif growth_avg >= 15:

            growth_component = 17

        elif growth_avg >= 10:

            growth_component = 14

        elif growth_avg >= 5:

            growth_component = 10

        elif growth_avg >= 0:

            growth_component = 6

        else:

            growth_component = 2

    # 盈利能力
    profitability_component = 0

    if annual_roe is not None:

        if annual_roe >= 20:

            profitability_component = 15

        elif annual_roe >= 15:

            profitability_component = 13

        elif annual_roe >= 10:

            profitability_component = 10

        elif annual_roe >= 5:

            profitability_component = 6

        else:

            profitability_component = 2

    # 现金流
    cash_component = 0

    if cash_profit_ratio is not None:

        if cash_profit_ratio >= 1:

            cash_component = 15

        elif cash_profit_ratio >= 0.8:

            cash_component = 13

        elif cash_profit_ratio >= 0.6:

            cash_component = 10

        elif cash_profit_ratio >= 0.3:

            cash_component = 6

        elif cash_profit_ratio >= 0:

            cash_component = 3

    # 财务安全
    safety_component = 0

    if annual_debt_ratio is not None:

        if annual_debt_ratio < 40:

            safety_component = 10

        elif annual_debt_ratio < 50:

            safety_component = 9

        elif annual_debt_ratio < 60:

            safety_component = 7

        elif annual_debt_ratio < 70:

            safety_component = 5

        else:

            safety_component = 2

    # 估值
    valuation_component = 0

    if valuation_gap is not None:

        if valuation_gap >= 30:

            valuation_component = 10

        elif valuation_gap >= 20:

            valuation_component = 9

        elif valuation_gap >= 10:

            valuation_component = 8

        elif valuation_gap >= 0:

            valuation_component = 6

        elif valuation_gap >= -10:

            valuation_component = 4

        elif valuation_gap >= -20:

            valuation_component = 2

    # 风险扣分
    if risk_score >= 6:

        risk_penalty = 12

    elif risk_score >= 4:

        risk_penalty = 8

    elif risk_score >= 2:

        risk_penalty = 4

    else:

        risk_penalty = 0

    final_score = round(
        max(
            0,
            min(
                100,
                financial_component
                + growth_component
                + profitability_component
                + cash_component
                + safety_component
                + valuation_component
                - risk_penalty
            )
        )
    )

    if final_score >= 85:

        final_rating = (
            "A：优秀长期价值候选"
        )

    elif final_score >= 75:

        final_rating = (
            "B：优质，值得长期跟踪"
        )

    elif final_score >= 65:

        final_rating = (
            "C：一般，等待更多验证"
        )

    elif final_score >= 50:

        final_rating = (
            "D：谨慎，不适合重仓"
        )

    else:

        final_rating = (
            "E：风险较高"
        )

    r1, r2 = st.columns(2)

    r1.metric(
        "ValueStock AI综合分",
        f"{final_score}/100"
    )

    r2.metric(
        "投资评级",
        final_rating
    )

    score_table = pd.DataFrame({

        "维度": [
            "财务质量",
            "成长性",
            "盈利能力",
            "现金流质量",
            "财务安全",
            "估值"
        ],

        "满分": [
            30,
            20,
            15,
            15,
            10,
            10
        ],

        "得分": [
            round(financial_component, 1),
            growth_component,
            profitability_component,
            cash_component,
            safety_component,
            valuation_component
        ]
    })

    st.dataframe(
        score_table,
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # 十四、最终投资结论
    # =====================================================

    st.header(
        "🏆 十四、最终投资结论"
    )

    if final_score >= 85:

        conclusion = (
            "公司综合质量优秀，"
            "具备长期重点研究价值。"
        )

    elif final_score >= 75:

        conclusion = (
            "公司综合质量较好，"
            "值得长期跟踪。"
        )

    elif final_score >= 65:

        conclusion = (
            "公司具备一定价值，"
            "但仍需要进一步验证。"
        )

    elif final_score >= 50:

        conclusion = (
            "公司存在一定风险，"
            "当前不适合重仓。"
        )

    else:

        conclusion = (
            "当前综合质量偏弱，"
            "不建议作为长期核心资产。"
        )

    st.info(
        conclusion
    )

    if risk_items:

        st.subheader(
            "⚠️ 重点风险"
        )

        for item in risk_items:

            st.write(
                f"- {item}"
            )

    # =====================================================
    # 十五、数据诊断
    # =====================================================

    st.header(
        "🛠️ 十五、数据诊断"
    )

    diagnostic = pd.DataFrame({

        "项目": [
            "实时/参考价格",
            "历史行情",
            "财务指标",
            "最新ROE",
            "年度ROE",
            "年度EPS",
            "年度BPS",
            "利润表",
            "资产负债表",
            "现金流量表",
            "经营现金流",
            "当前PE",
            "当前PB",
            "合理价",
            "建仓价",
            "重仓价"
        ],

        "状态": [

            "✅"
            if current_price is not None
            else "❌",

            "✅"
            if history is not None
            else "❌",

            "✅"
            if indicators is not None
            else "❌",

            "✅"
            if latest_roe is not None
            else "❌",

            "✅"
            if annual_roe is not None
            else "❌",

            "✅"
            if annual_eps is not None
            else "❌",

            "✅"
            if annual_bvps is not None
            else "❌",

            "✅"
            if profit is not None
            else "❌",

            "✅"
            if balance is not None
            else "❌",

            "✅"
            if cashflow is not None
            else "❌",

            "✅"
            if latest_cashflow is not None
            else "❌",

            "✅"
            if current_pe is not None
            else "❌",

            "✅"
            if current_pb is not None
            else "❌",

            "✅"
            if normal_value is not None
            else "❌",

            "✅"
            if entry_price is not None
            else "❌",

            "✅"
            if heavy_price is not None
            else "❌"
        ]
    })

    st.dataframe(
        diagnostic,
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # 十六、说明
    # =====================================================

    with st.expander(
        "📖 估值与数据口径说明"
    ):

        st.write(
            "最新报告期数据：主要用于判断近期经营状态。"
        )

        st.write(
            "最近完整年度数据：主要用于长期价值投资和估值。"
        )

        st.write(
            "当前PE = 当前价格 ÷ 年度EPS。"
        )

        st.write(
            "PB = 当前价格 ÷ 年度每股净资产。"
        )

        st.write(
            "PE/PB综合估值用于安全边际研究，不是未来股价预测。"
        )

        st.write(
            "建仓参考价 = 中性合理价 × 85%。"
        )

        st.write(
            "重仓参考价 = 中性合理价 × 70%。"
        )

        st.write(
            "当前版本尚未加入历史PE分位、同行估值、DCF和未来盈利预测。"
        )

    st.divider()

    st.caption(
        "ValueStock AI V12.2：稳定数据链路 + "
        "财务质量 + 财务排雷 + 三情景估值 + 综合投资评级。"
    )
# =====================================================
# V13：历史估值分位分析
# =====================================================

st.divider()

st.header("📊 V13：历史估值分位")

st.caption(
    "利用年度EPS与对应年度最后交易日收盘价，"
    "计算历史PE，用于判断当前估值处于自身历史什么位置。"
)


# =====================================================
# 1. 准备历史价格
# =====================================================

historical_pe = pd.DataFrame()


if (
    history is not None
    and not history.empty
    and trend is not None
    and not trend.empty
):

    price_df = history.copy()


    # -------------------------------------------------
    # 统一日期字段
    # -------------------------------------------------

    if "日期" in price_df.columns:

        price_df["_日期"] = pd.to_datetime(
            price_df["日期"],
            errors="coerce"
        )

        price_df["_收盘价"] = (
            price_df["收盘"]
            .apply(safe_float)
        )

    elif "date" in price_df.columns:

        price_df["_日期"] = pd.to_datetime(
            price_df["date"],
            errors="coerce"
        )

        price_df["_收盘价"] = (
            price_df["close"]
            .apply(safe_float)
        )

    else:

        price_df = pd.DataFrame()


    if not price_df.empty:

        price_df = price_df.dropna(
            subset=[
                "_日期",
                "_收盘价"
            ]
        )


    # -------------------------------------------------
    # 获取每年的最后交易日
    # -------------------------------------------------

    if not price_df.empty:

        price_df["年份"] = (
            price_df["_日期"].dt.year
        )

        year_end_price = (
            price_df
            .sort_values("_日期")
            .groupby("年份")
            .tail(1)
        )


        # -------------------------------------------------
        # 处理财务趋势数据
        # -------------------------------------------------

        trend_v13 = trend.copy()


        if (
            "报告期" in trend_v13.columns
            and "EPS" in trend_v13.columns
        ):

            trend_v13["_报告日期"] = (
                pd.to_datetime(
                    trend_v13["报告期"],
                    errors="coerce"
                )
            )

            trend_v13["年份"] = (
                trend_v13["_报告日期"]
                .dt.year
            )

            trend_v13["EPS"] = (
                trend_v13["EPS"]
                .apply(safe_float)
            )


            trend_v13 = trend_v13[
                [
                    "年份",
                    "EPS"
                ]
            ].dropna(
                subset=["EPS"]
            )


            # -------------------------------------------------
            # 合并年度价格与EPS
            # -------------------------------------------------

            historical_pe = pd.merge(
                year_end_price[
                    [
                        "年份",
                        "_日期",
                        "_收盘价"
                    ]
                ],
                trend_v13,
                on="年份",
                how="inner"
            )


            historical_pe = historical_pe[
                historical_pe["EPS"] > 0
            ].copy()


            if not historical_pe.empty:

                historical_pe["PE"] = (
                    historical_pe["_收盘价"]
                    / historical_pe["EPS"]
                )


                historical_pe = (
                    historical_pe
                    .sort_values("年份")
                    .tail(5)
                )


# =====================================================
# 2. 显示历史PE
# =====================================================

if (
    historical_pe is not None
    and not historical_pe.empty
):

    display_pe = pd.DataFrame({

        "年份":
            historical_pe["年份"].astype(str),

        "年末收盘价":
            historical_pe["_收盘价"].round(2),

        "年度EPS":
            historical_pe["EPS"].round(2),

        "历史PE":
            historical_pe["PE"].round(2)

    })


    st.subheader(
        "📅 最近5年历史PE"
    )


    st.dataframe(
        display_pe,
        use_container_width=True,
        hide_index=True
    )


    # =================================================
    # 3. 历史PE统计
    # =================================================

    pe_values = (
        historical_pe["PE"]
        .dropna()
        .tolist()
    )


    if len(pe_values) >= 2:

        historical_pe_min = min(
            pe_values
        )

        historical_pe_max = max(
            pe_values
        )

        historical_pe_median = (
            pd.Series(pe_values)
            .median()
        )

        historical_pe_mean = (
            pd.Series(pe_values)
            .mean()
        )


        st.subheader(
            "📊 历史PE统计"
        )


        h1, h2, h3, h4 = st.columns(4)


        h1.metric(
            "历史最低PE",
            f"{historical_pe_min:.2f}"
        )


        h2.metric(
            "历史中位PE",
            f"{historical_pe_median:.2f}"
        )


        h3.metric(
            "历史平均PE",
            f"{historical_pe_mean:.2f}"
        )


        h4.metric(
            "历史最高PE",
            f"{historical_pe_max:.2f}"
        )


        # =================================================
        # 4. 当前PE历史分位
        # =================================================

        if current_pe is not None:

            lower_count = sum(
                1
                for x in pe_values
                if x <= current_pe
            )


            historical_percentile = (
                lower_count
                / len(pe_values)
                * 100
            )


            st.subheader(
                "🎯 当前PE历史分位"
            )


            st.metric(
                "当前PE历史分位",
                f"{historical_percentile:.1f}%"
            )


            if historical_percentile <= 20:

                st.success(
                    "🟢 当前估值处于历史偏低区域，"
                    "安全边际相对较好。"
                )


            elif historical_percentile <= 40:

                st.success(
                    "🟢 当前估值处于历史中低区域。"
                )


            elif historical_percentile <= 60:

                st.info(
                    "🟡 当前估值处于历史中枢附近。"
                )


            elif historical_percentile <= 80:

                st.warning(
                    "🟠 当前估值处于历史中高区域。"
                )


            else:

                st.error(
                    "🔴 当前估值处于历史高位。"
                )


        # =================================================
        # 5. 当前PE vs 历史中位数
        # =================================================

        if current_pe is not None:

            deviation = (
                current_pe
                / historical_pe_median
                - 1
            ) * 100


            st.subheader(
                "🔍 当前PE与历史中位数比较"
            )


            st.metric(
                "相对历史中位PE偏离",
                f"{deviation:.2f}%"
            )


            if deviation <= -20:

                st.success(
                    "🟢 当前PE明显低于历史中位水平。"
                )

            elif deviation <= -10:

                st.success(
                    "🟢 当前PE低于历史中位水平。"
                )

            elif deviation <= 10:

                st.info(
                    "🟡 当前PE接近历史估值中枢。"
                )

            elif deviation <= 20:

                st.warning(
                    "🟠 当前PE高于历史中位水平。"
                )

            else:

                st.error(
                    "🔴 当前PE明显高于历史中位水平。"
                )


else:

    st.warning(
        "⚠️ 当前数据不足，"
        "暂时无法建立有效的历史PE序列。"
    )


# =====================================================
# 6. V13估值结论
# =====================================================

st.subheader(
    "🏆 V13历史估值结论"
)


if (
    historical_pe is not None
    and not historical_pe.empty
    and current_pe is not None
):

    pe_values = (
        historical_pe["PE"]
        .dropna()
        .tolist()
    )


    if len(pe_values) >= 2:

        median_pe = (
            pd.Series(pe_values)
            .median()
        )


        percentile = (
            sum(
                1
                for x in pe_values
                if x <= current_pe
            )
            / len(pe_values)
            * 100
        )


        if percentile <= 20:

            st.success(
                f"🟢 V13判断：当前PE {current_pe:.2f}倍，"
                f"处于历史较低区域。"
            )


        elif percentile <= 40:

            st.success(
                f"🟢 V13判断：当前PE {current_pe:.2f}倍，"
                f"处于历史中低区域。"
            )


        elif percentile <= 60:

            st.info(
                f"🟡 V13判断：当前PE {current_pe:.2f}倍，"
                f"接近历史估值中枢。"
            )


        elif percentile <= 80:

            st.warning(
                f"🟠 V13判断：当前PE {current_pe:.2f}倍，"
                f"处于历史中高区域。"
            )


        else:

            st.error(
                f"🔴 V13判断：当前PE {current_pe:.2f}倍，"
                f"处于历史高位区域。"
            )

else:

    st.info(
        "V13暂时缺少足够的历史EPS/价格配对数据。"
    )


st.caption(
    "V13说明：历史PE仅用于估值参考。"
    "周期股、利润波动较大的公司不能机械使用历史PE分位。"
)
# =====================================================
# V14：同行业比较（独立稳定版）
# =====================================================

st.divider()

st.header("🏭 V14：同行业比较")

st.caption(
    "独立同行比较模块：输入目标公司和2～5家可比公司，"
    "系统自动获取财务指标并进行横向比较。"
)


# =====================================================
# 1. 输入目标公司
# =====================================================

peer_target_input = st.text_input(
    "目标公司股票代码",
    placeholder="例如：600089"
)


peer_input = st.text_input(
    "同行公司代码（2～5只，英文逗号分隔）",
    placeholder="例如：600406,002028,601179"
)


peer_compare_button = st.button(
    "🔍 开始同行比较",
    key="peer_compare_button"
)


# =====================================================
# 2. 开始比较
# =====================================================

if peer_compare_button:

    target_code = clean_stock_code(
        peer_target_input
    )

    if not target_code:

        st.error(
            "❌ 目标公司请输入6位股票代码"
        )

        st.stop()


    # -------------------------------------------------
    # 处理同行代码
    # -------------------------------------------------

    peer_codes = []

    if peer_input:

        raw_codes = peer_input.split(",")

        for code in raw_codes:

            clean_code = clean_stock_code(
                code
            )

            if (
                clean_code
                and clean_code != target_code
                and clean_code not in peer_codes
            ):

                peer_codes.append(
                    clean_code
                )


    if len(peer_codes) < 2:

        st.warning(
            "⚠️ 至少需要输入2只同行公司。"
        )

        st.stop()


    if len(peer_codes) > 5:

        peer_codes = peer_codes[:5]

        st.info(
            "最多比较5家公司，已自动取前5只。"
        )


    compare_codes = [
        target_code
    ] + peer_codes


    # =================================================
    # 3. 获取公司数据
    # =================================================

    rows = []


    progress = st.progress(0)

    total = len(compare_codes)


    for index, code in enumerate(
        compare_codes
    ):

        try:

            # -----------------------------------------
            # 财务数据
            # -----------------------------------------

            indicators, source = (
                get_financial_indicators(
                    code
                )
            )


            if (
                indicators is None
                or indicators.empty
            ):

                st.warning(
                    f"⚠️ {code} 财务数据获取失败。"
                )

                continue


            financial = (
                process_financial_indicators(
                    indicators
                )
            )


            annual = financial[
                "annual"
            ]


            # -----------------------------------------
            # 当前价格
            # -----------------------------------------

            market = get_realtime_market(
                code
            )


            name = code

            price = None


            if market:

                name = market.get(
                    "名称",
                    code
                )

                price = safe_float(
                    market.get(
                        "最新价"
                    )
                )


            # -----------------------------------------
            # 历史价格兜底
            # -----------------------------------------

            if price is None:

                history_data = (
                    get_history_data(
                        code
                    )
                )


                price = (
                    get_history_latest_price(
                        history_data
                    )
                )


            # -----------------------------------------
            # PE
            # -----------------------------------------

            eps = annual.get(
                "eps"
            )


            pe = None


            if (
                price is not None
                and eps is not None
                and eps > 0
            ):

                pe = (
                    price
                    / eps
                )


            # -----------------------------------------
            # PB
            # -----------------------------------------

            bvps = annual.get(
                "bvps"
            )


            pb = None


            if (
                price is not None
                and bvps is not None
                and bvps > 0
            ):

                pb = (
                    price
                    / bvps
                )


            rows.append({

                "代码": code,

                "名称": name,

                "价格": price,

                "ROE": annual.get(
                    "roe"
                ),

                "营收增长率": annual.get(
                    "revenue_growth"
                ),

                "净利润增长率": annual.get(
                    "profit_growth"
                ),

                "资产负债率": annual.get(
                    "debt"
                ),

                "EPS": eps,

                "BPS": bvps,

                "PE": pe,

                "PB": pb

            })


        except Exception as e:

            st.warning(
                f"⚠️ {code} 获取失败：{e}"
            )


        progress.progress(
            (index + 1)
            / total
        )


    # =================================================
    # 4. 比较结果
    # =================================================

    if len(rows) < 2:

        st.error(
            "❌ 有效公司数量不足，无法进行同行比较。"
        )

        st.stop()


    compare_df = pd.DataFrame(
        rows
    )


    st.success(
        f"✅ 成功获取 {len(compare_df)} 家公司的数据。"
    )


    # =================================================
    # 5. 核心比较表
    # =================================================

    st.subheader(
        "📊 同行业核心指标比较"
    )


    display_df = compare_df.copy()


    numeric_columns = [

        "价格",
        "ROE",
        "营收增长率",
        "净利润增长率",
        "资产负债率",
        "EPS",
        "BPS",
        "PE",
        "PB"

    ]


    for col in numeric_columns:

        if col in display_df.columns:

            display_df[col] = (
                display_df[col]
                .apply(
                    lambda x:
                    "暂无"
                    if pd.isna(x)
                    else round(
                        float(x),
                        2
                    )
                )
            )


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


    # =================================================
    # 6. 行业平均
    # =================================================

    st.subheader(
        "📊 可比公司平均水平"
    )


    average_columns = [

        "ROE",
        "营收增长率",
        "净利润增长率",
        "资产负债率",
        "PE",
        "PB"

    ]


    average_data = []


    for col in average_columns:

        if col in compare_df.columns:

            average_data.append({

                "指标": col,

                "可比公司平均": (
                    compare_df[col]
                    .mean()
                )

            })


    if average_data:

        average_df = pd.DataFrame(
            average_data
        )


        average_df[
            "可比公司平均"
        ] = (
            average_df[
                "可比公司平均"
            ]
            .round(2)
        )


        st.dataframe(
            average_df,
            use_container_width=True,
            hide_index=True
        )


    # =================================================
    # 7. 找到目标公司
    # =================================================

    target_rows = compare_df[
        compare_df["代码"]
        == target_code
    ]


    if target_rows.empty:

        st.warning(
            "⚠️ 目标公司数据未成功获取。"
        )

        st.stop()


    target = target_rows.iloc[0]


    # =================================================
    # 8. 行业相对评价
    # =================================================

    st.subheader(
        "🎯 目标公司同行相对位置"
    )


    # -------------------------------------------------
    # ROE
    # -------------------------------------------------

    if "ROE" in compare_df.columns:

        roe_average = (
            compare_df["ROE"]
            .mean()
        )

        target_roe = target["ROE"]


        if not pd.isna(target_roe):

            if target_roe > roe_average:

                st.success(
                    f"✅ ROE {target_roe:.2f}% "
                    f"高于同行平均 "
                    f"{roe_average:.2f}%。"
                )

            else:

                st.warning(
                    f"🟡 ROE {target_roe:.2f}% "
                    f"低于或接近同行平均 "
                    f"{roe_average:.2f}%。"
                )


    # -------------------------------------------------
    # 营收增长
    # -------------------------------------------------

    if "营收增长率" in compare_df.columns:

        revenue_average = (
            compare_df["营收增长率"]
            .mean()
        )

        target_revenue = (
            target["营收增长率"]
        )


        if not pd.isna(
            target_revenue
        ):

            if target_revenue > revenue_average:

                st.success(
                    f"✅ 营收增长 "
                    f"{target_revenue:.2f}% "
                    f"高于同行平均 "
                    f"{revenue_average:.2f}%。"
                )

            else:

                st.warning(
                    f"🟡 营收增长 "
                    f"{target_revenue:.2f}% "
                    f"低于或接近同行平均 "
                    f"{revenue_average:.2f}%。"
                )


    # -------------------------------------------------
    # 净利润增长
    # -------------------------------------------------

    if "净利润增长率" in compare_df.columns:

        profit_average = (
            compare_df[
                "净利润增长率"
            ].mean()
        )

        target_profit = (
            target["净利润增长率"]
        )


        if not pd.isna(
            target_profit
        ):

            if target_profit > profit_average:

                st.success(
                    f"✅ 净利润增长 "
                    f"{target_profit:.2f}% "
                    f"高于同行平均 "
                    f"{profit_average:.2f}%。"
                )

            else:

                st.warning(
                    f"🟡 净利润增长 "
                    f"{target_profit:.2f}% "
                    f"低于或接近同行平均 "
                    f"{profit_average:.2f}%。"
                )


    # -------------------------------------------------
    # PE
    # -------------------------------------------------

    if "PE" in compare_df.columns:

        pe_average = (
            compare_df["PE"]
            .mean()
        )

        target_pe = target["PE"]


        if (
            not pd.isna(target_pe)
            and not pd.isna(pe_average)
        ):

            if target_pe < pe_average:

                st.success(
                    f"🟢 PE {target_pe:.2f}倍，"
                    f"低于同行平均 "
                    f"{pe_average:.2f}倍。"
                )

            else:

                st.warning(
                    f"🟠 PE {target_pe:.2f}倍，"
                    f"高于同行平均 "
                    f"{pe_average:.2f}倍。"
                )


    # -------------------------------------------------
    # PB
    # -------------------------------------------------

    if "PB" in compare_df.columns:

        pb_average = (
            compare_df["PB"]
            .mean()
        )

        target_pb = target["PB"]


        if (
            not pd.isna(target_pb)
            and not pd.isna(pb_average)
        ):

            if target_pb < pb_average:

                st.success(
                    f"🟢 PB {target_pb:.2f}倍，"
                    f"低于同行平均 "
                    f"{pb_average:.2f}倍。"
                )

            else:

                st.warning(
                    f"🟠 PB {target_pb:.2f}倍，"
                    f"高于同行平均 "
                    f"{pb_average:.2f}倍。"
                )


    # =================================================
    # 9. 同行竞争力评分
    # =================================================

    st.subheader(
        "🏆 同行竞争力评分"
    )


    peer_score = 0


    # ROE 30分
    if (
        "ROE" in compare_df.columns
        and not pd.isna(target["ROE"])
    ):

        roe_rank = (
            compare_df["ROE"]
            .rank(
                ascending=False,
                method="min"
            )
        )


        rank = roe_rank[
            target.name
        ]


        if rank == 1:

            peer_score += 30

        elif rank == 2:

            peer_score += 25

        elif rank <= 3:

            peer_score += 20

        else:

            peer_score += 10


    # 营收增长 25分
    if (
        "营收增长率"
        in compare_df.columns
        and not pd.isna(
            target["营收增长率"]
        )
    ):

        rank = (
            compare_df[
                "营收增长率"
            ]
            .rank(
                ascending=False,
                method="min"
            )
            .loc[target.name]
        )


        if rank == 1:

            peer_score += 25

        elif rank == 2:

            peer_score += 20

        elif rank <= 3:

            peer_score += 15

        else:

            peer_score += 8


    # PE 25分
    if (
        "PE" in compare_df.columns
        and not pd.isna(
            target["PE"]
        )
    ):

        valid_pe = compare_df[
            "PE"
        ].dropna()


        if not valid_pe.empty:

            rank = (
                valid_pe
                .rank(
                    ascending=True,
                    method="min"
                )
            )


            if target.name in rank.index:

                target_rank = rank[
                    target.name
                ]


                if target_rank == 1:

                    peer_score += 25

                elif target_rank == 2:

                    peer_score += 20

                elif target_rank <= 3:

                    peer_score += 15

                else:

                    peer_score += 8


    # 负债率 20分
    if (
        "资产负债率"
        in compare_df.columns
        and not pd.isna(
            target["资产负债率"]
        )
    ):

        valid_debt = (
            compare_df[
                "资产负债率"
            ]
            .dropna()
        )


        if not valid_debt.empty:

            rank = (
                valid_debt
                .rank(
                    ascending=True,
                    method="min"
                )
            )


            if target.name in rank.index:

                target_rank = rank[
                    target.name
                ]


                if target_rank == 1:

                    peer_score += 20

                elif target_rank == 2:

                    peer_score += 16

                elif target_rank <= 3:

                    peer_score += 12

                else:

                    peer_score += 6


    # -------------------------------------------------
    # 评级
    # -------------------------------------------------

    if peer_score >= 85:

        peer_rating = "优秀"

    elif peer_score >= 70:

        peer_rating = "良好"

    elif peer_score >= 55:

        peer_rating = "一般"

    else:

        peer_rating = "偏弱"


    c1, c2 = st.columns(2)


    c1.metric(
        "同行竞争力得分",
        f"{peer_score}/100"
    )


    c2.metric(
        "同行竞争力评级",
        peer_rating
    )


    if peer_score >= 85:

        st.success(
            "🟢 目标公司在当前可比公司中综合竞争力较强。"
        )

    elif peer_score >= 70:

        st.info(
            "🟡 目标公司在当前可比公司中具备较好的竞争力。"
        )

    elif peer_score >= 55:

        st.warning(
            "🟠 目标公司在当前可比公司中处于中等水平。"
        )

    else:

        st.error(
            "🔴 目标公司在当前可比公司中竞争力偏弱。"
        )


st.divider()

st.caption(
    "V14：独立同行比较模块。"
    "目前同行由用户选择，避免自动行业分类误匹配。"
)
