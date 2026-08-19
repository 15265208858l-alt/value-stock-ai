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
st.subheader("A股长期价值投资分析系统 V12")

st.caption(
    "实时行情 + 最新季度经营 + 完整年度盈利 + 5年财务质量 + "
    "财务排雷 + PE/PB估值 + 安全边际"
)

st.divider()


# =========================================================
# 1. 基础工具函数
# =========================================================

def clean_stock_code(code):
    """
    清理股票代码
    """

    if code is None:
        return ""

    code = str(code).strip()

    if len(code) != 6:
        return ""

    if not code.isdigit():
        return ""

    return code


def get_symbol_with_market(stock_code):
    """
    转换成 SH000000 / SZ000000
    """

    if stock_code.startswith(("6", "68")):
        return "SH" + stock_code

    elif stock_code.startswith(("0", "3")):
        return "SZ" + stock_code

    elif stock_code.startswith(("4", "8")):
        return "BJ" + stock_code

    return stock_code


def safe_float(value):
    """
    安全转换数字
    """

    try:

        if value is None:
            return None

        if isinstance(value, float):

            if math.isnan(value):
                return None

        text = str(value).strip()

        if text in [
            "",
            "--",
            "None",
            "none",
            "nan",
            "NaN",
            "null",
            "NULL"
        ]:
            return None

        text = text.replace(",", "")
        text = text.replace("%", "")

        return float(text)

    except Exception:

        return None


def find_column(df, candidates):
    """
    寻找字段
    """

    if df is None:
        return None

    if df.empty:
        return None

    for col in candidates:

        if col in df.columns:

            return col

    return None


def to_date_series(df, candidates):
    """
    查找日期字段并转换
    """

    date_col = find_column(
        df,
        candidates
    )

    if date_col is None:
        return None, None

    result = df.copy()

    result["_分析日期"] = pd.to_datetime(
        result[date_col],
        errors="coerce"
    )

    result = (
        result
        .dropna(subset=["_分析日期"])
        .sort_values(
            "_分析日期",
            ascending=False
        )
        .reset_index(drop=True)
    )

    return result, date_col


def is_annual_date(value):
    """
    判断是否为年报日期
    """

    try:

        date = pd.to_datetime(
            value,
            errors="coerce"
        )

        if pd.isna(date):
            return False

        return (
            date.month == 12
            and date.day == 31
        )

    except Exception:

        return False


def safe_ratio(a, b):

    if a is None:
        return None

    if b is None:
        return None

    if b == 0:
        return None

    return a / b


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
            [
                "代码",
                "股票代码"
            ]
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
def get_history(stock_code):

    try:

        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date="20200101",
            end_date="20500101",
            adjust=""
        )

        if df is not None and not df.empty:

            return df

    except Exception:
        pass


    try:

        market_code = (
            "sh" + stock_code
            if stock_code.startswith(("6", "68"))
            else
            "sz" + stock_code
        )

        df = ak.stock_zh_a_hist_tx(
            symbol=market_code,
            start_date="20200101",
            end_date="20500101",
            adjust=""
        )

        if df is not None and not df.empty:

            return df

    except Exception:
        pass


    return None


# =========================================================
# 4. 东方财富财务指标
# =========================================================

@st.cache_data(ttl=3600)
def get_financial_indicators(stock_code):

    try:

        df = ak.stock_financial_analysis_indicator_em(
            symbol=stock_code,
            indicator="按报告期"
        )

        if df is not None and not df.empty:

            return df

    except Exception:

        pass


    return None


# =========================================================
# 5. 三张财务报表
# =========================================================

@st.cache_data(ttl=3600)
def get_profit_sheet(stock_code):

    try:

        df = ak.stock_profit_sheet_by_report_em(
            symbol=get_symbol_with_market(
                stock_code
            )
        )

        if df is not None and not df.empty:

            return df

    except Exception:

        pass


    # 第二次尝试不带市场前缀
    try:

        df = ak.stock_profit_sheet_by_report_em(
            symbol=stock_code
        )

        if df is not None and not df.empty:

            return df

    except Exception:

        pass


    return None


@st.cache_data(ttl=3600)
def get_balance_sheet(stock_code):

    try:

        df = ak.stock_balance_sheet_by_report_em(
            symbol=get_symbol_with_market(
                stock_code
            )
        )

        if df is not None and not df.empty:

            return df

    except Exception:

        pass


    try:

        df = ak.stock_balance_sheet_by_report_em(
            symbol=stock_code
        )

        if df is not None and not df.empty:

            return df

    except Exception:

        pass


    return None


@st.cache_data(ttl=3600)
def get_cashflow_sheet(stock_code):

    try:

        df = ak.stock_cash_flow_sheet_by_report_em(
            symbol=get_symbol_with_market(
                stock_code
            )
        )

        if df is not None and not df.empty:

            return df

    except Exception:

        pass


    try:

        df = ak.stock_cash_flow_sheet_by_report_em(
            symbol=stock_code
        )

        if df is not None and not df.empty:

            return df

    except Exception:

        pass


    return None


# =========================================================
# 6. 提取财务指标
# =========================================================

def extract_financial_metrics(indicators):

    result = {

        # 最新报告期
        "latest": {},

        # 最近完整年度
        "annual": {},

        # 5年数据
        "trend": pd.DataFrame()

    }


    if indicators is None or indicators.empty:

        return result


    df = indicators.copy()


    # -----------------------------------------------------
    # 日期处理
    # -----------------------------------------------------

    df, date_col = to_date_series(
        df,
        [
            "REPORT_DATE",
            "报告日期",
            "报告期",
            "日期",
            "截止日期"
        ]
    )


    if df is None or df.empty:

        return result


    # -----------------------------------------------------
    # 字段
    # -----------------------------------------------------

    roe_col = find_column(
        df,
        [
            "ROEJQ",
            "加权净资产收益率(%)",
            "加权净资产收益率",
            "净资产收益率(%)",
            "净资产收益率"
        ]
    )


    revenue_growth_col = find_column(
        df,
        [
            "TOTALOPERATEREVETZ",
            "主营业务收入增长率(%)",
            "主营业务收入增长率",
            "营业收入增长率(%)",
            "营业收入增长率"
        ]
    )


    profit_growth_col = find_column(
        df,
        [
            "PARENTNETPROFITTZ",
            "净利润增长率(%)",
            "净利润增长率",
            "归属净利润同比增长(%)"
        ]
    )


    debt_col = find_column(
        df,
        [
            "ZCFZL",
            "资产负债率(%)",
            "资产负债率"
        ]
    )


    eps_col = find_column(
        df,
        [
            "EPSJB",
            "基本每股收益(元)",
            "基本每股收益",
            "摊薄每股收益(元)",
            "摊薄每股收益",
            "每股收益(元)",
            "每股收益"
        ]
    )


    bvps_col = find_column(
        df,
        [
            "BPS",
            "每股净资产(元)",
            "每股净资产",
            "归属母公司股东的每股净资产"
        ]
    )


    cash_per_share_col = find_column(
        df,
        [
            "MGJYXJJE",
            "每股经营性现金流(元)",
            "每股经营性现金流"
        ]
    )


    # -----------------------------------------------------
    # 最新报告期
    # -----------------------------------------------------

    latest = df.iloc[0]


    latest_data = {

        "report_date": (
            latest[date_col]
            if date_col
            else None
        ),

        "roe": (
            safe_float(latest[roe_col])
            if roe_col
            else None
        ),

        "revenue_growth": (
            safe_float(
                latest[revenue_growth_col]
            )
            if revenue_growth_col
            else None
        ),

        "profit_growth": (
            safe_float(
                latest[profit_growth_col]
            )
            if profit_growth_col
            else None
        ),

        "debt_ratio": (
            safe_float(latest[debt_col])
            if debt_col
            else None
        ),

        "eps": (
            safe_float(latest[eps_col])
            if eps_col
            else None
        ),

        "bvps": (
            safe_float(latest[bvps_col])
            if bvps_col
            else None
        ),

        "cash_per_share": (
            safe_float(
                latest[cash_per_share_col]
            )
            if cash_per_share_col
            else None
        )

    }


    result["latest"] = latest_data


    # -----------------------------------------------------
    # 最近完整年度
    # -----------------------------------------------------

    annual_df = df[
        df["_分析日期"].apply(
            is_annual_date
        )
    ].copy()


    if not annual_df.empty:

        annual = annual_df.iloc[0]

        annual_data = {

            "report_date": (
                annual[date_col]
                if date_col
                else None
            ),

            "roe": (
                safe_float(
                    annual[roe_col]
                )
                if roe_col
                else None
            ),

            "revenue_growth": (
                safe_float(
                    annual[
                        revenue_growth_col
                    ]
                )
                if revenue_growth_col
                else None
            ),

            "profit_growth": (
                safe_float(
                    annual[
                        profit_growth_col
                    ]
                )
                if profit_growth_col
                else None
            ),

            "debt_ratio": (
                safe_float(
                    annual[debt_col]
                )
                if debt_col
                else None
            ),

            "eps": (
                safe_float(
                    annual[eps_col]
                )
                if eps_col
                else None
            ),

            "bvps": (
                safe_float(
                    annual[bvps_col]
                )
                if bvps_col
                else None
            ),

            "cash_per_share": (
                safe_float(
                    annual[
                        cash_per_share_col
                    ]
                )
                if cash_per_share_col
                else None
            )

        }

    else:

        annual_data = {

            "report_date": None,
            "roe": None,
            "revenue_growth": None,
            "profit_growth": None,
            "debt_ratio": None,
            "eps": None,
            "bvps": None,
            "cash_per_share": None

        }


    # -----------------------------------------------------
    # 年度缺失保护
    # -----------------------------------------------------

    for key in annual_data:

        if annual_data[key] is None:

            if key in latest_data:

                annual_data[key] = (
                    latest_data[key]
                )


    result["annual"] = annual_data


    # -----------------------------------------------------
    # 5年趋势
    # -----------------------------------------------------

    trend = df[
        [
            "_分析日期"
        ]
        + (
            [roe_col]
            if roe_col
            else []
        )
        + (
            [revenue_growth_col]
            if revenue_growth_col
            else []
        )
        + (
            [profit_growth_col]
            if profit_growth_col
            else []
        )
        + (
            [debt_col]
            if debt_col
            else []
        )
        + (
            [eps_col]
            if eps_col
            else []
        )
    ].copy()


    trend["年份"] = (
        trend["_分析日期"]
        .dt.year
    )


    # 优先使用每年的12月31日
    annual_trend = trend[
        trend["_分析日期"].dt.month == 12
    ].copy()


    if not annual_trend.empty:

        annual_trend = (
            annual_trend
            .sort_values(
                "_分析日期"
            )
            .groupby("年份")
            .tail(1)
            .tail(5)
        )

    else:

        annual_trend = (
            trend
            .sort_values(
                "_分析日期"
            )
            .tail(5)
        )


    rename_dict = {

        "_分析日期": "报告日期"

    }


    if roe_col:

        rename_dict[
            roe_col
        ] = "ROE"


    if revenue_growth_col:

        rename_dict[
            revenue_growth_col
        ] = "营收增长率"


    if profit_growth_col:

        rename_dict[
            profit_growth_col
        ] = "净利润增长率"


    if debt_col:

        rename_dict[
            debt_col
        ] = "资产负债率"


    if eps_col:

        rename_dict[
            eps_col
        ] = "EPS"


    annual_trend = (
        annual_trend
        .rename(
            columns=rename_dict
        )
    )


    result["trend"] = annual_trend


    return result


# =========================================================
# 7. 报表字段提取
# =========================================================

def extract_report_value(
    df,
    candidates
):

    if df is None:
        return None

    if df.empty:
        return None

    data, date_col = to_date_series(
        df,
        [
            "REPORT_DATE",
            "报告期",
            "报告日",
            "报告日期",
            "截止日期",
            "日期"
        ]
    )

    if data is None or data.empty:
        return None

    col = find_column(
        data,
        candidates
    )

    if col is None:
        return None

    return safe_float(
        data.iloc[0][col]
    )


def extract_report_metrics(
    profit,
    balance,
    cashflow
):

    result = {

        "revenue": None,
        "net_profit": None,
        "receivable": None,
        "inventory": None,
        "operating_cashflow": None

    }


    result["revenue"] = extract_report_value(
        profit,
        [
            "营业总收入",
            "营业收入",
            "营业总收入(元)"
        ]
    )


    result["net_profit"] = extract_report_value(
        profit,
        [
            "归属于母公司股东的净利润",
            "归属于母公司所有者的净利润",
            "净利润"
        ]
    )


    result["receivable"] = extract_report_value(
        balance,
        [
            "应收账款"
        ]
    )


    result["inventory"] = extract_report_value(
        balance,
        [
            "存货"
        ]
    )


    result["operating_cashflow"] = extract_report_value(
        cashflow,
        [
            "经营活动产生的现金流量净额",
            "经营活动现金流量净额"
        ]
    )


    return result


# =========================================================
# 8. 输入区
# =========================================================

stock_input = st.text_input(
    "请输入A股股票代码",
    placeholder="例如：000333、600519、601899",
    value=""
)


analyze_button = st.button(
    "🚀 开始价值投资分析",
    type="primary"
)


# =========================================================
# 9. 初始化变量
# =========================================================

stock_code = ""

market_data = None
history = None
indicators = None

profit = None
balance = None
cashflow = None

latest_metrics = {}
annual_metrics = {}

roe = None
revenue_growth = None
profit_growth = None
debt_ratio = None

latest_roe = None
latest_revenue_growth = None
latest_profit_growth = None
latest_debt_ratio = None

valuation_price = None

annual_eps = None
annual_bvps = None

current_pe = None
current_pb = None

latest_revenue = None
latest_profit = None
latest_receivable = None
latest_inventory = None
latest_cashflow = None

cash_profit_ratio = None
receivable_ratio = None
inventory_ratio = None

risk_score = 0
risk_items = []

financial_quality_score = 0
financial_rating = "数据不足"


# =========================================================
# 10. 主程序
# =========================================================

if analyze_button:

    # -----------------------------------------------------
    # 股票代码
    # -----------------------------------------------------

    stock_code = clean_stock_code(
        stock_input
    )


    if not stock_code:

        st.error(
            "❌ 股票代码必须是6位数字，例如：000333"
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


    if market_data is not None:

        name = market_data.get(
            "名称",
            stock_code
        )


        valuation_price = safe_float(
            market_data.get(
                "最新价"
            )
        )


        day_change = safe_float(
            market_data.get(
                "涨跌幅"
            )
        )


        dynamic_pe = safe_float(
            market_data.get(
                "市盈率-动态"
            )
        )


        market_pb = safe_float(
            market_data.get(
                "市净率"
            )
        )


        c1, c2, c3, c4 = st.columns(4)


        c1.metric(
            "股票名称",
            str(name)
        )


        c2.metric(
            "当前价格",
            "暂无"
            if valuation_price is None
            else f"{valuation_price:.2f} 元"
        )


        c3.metric(
            "当日涨跌幅",
            "暂无"
            if day_change is None
            else f"{day_change:.2f}%"
        )


        c4.metric(
            "实时动态PE",
            "暂无"
            if dynamic_pe is None
            else f"{dynamic_pe:.2f} 倍"
        )


        if market_pb is not None:

            current_pb = market_pb


        st.success(
            "✅ 实时行情获取成功"
        )


    else:

        st.error(
            "❌ 实时行情获取失败"
        )


    # =====================================================
    # 二、历史行情
    # =====================================================

    st.header("📈 二、历史行情")


    history = get_history(
        stock_code
    )


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
            "⚠️ 历史行情暂时无法获取"
        )


    # =====================================================
    # 三、财务指标
    # =====================================================

    st.header(
        "📊 三、财务指标"
    )


    indicators = get_financial_indicators(
        stock_code
    )


    if indicators is None:

        st.error(
            "❌ 财务指标获取失败"
        )

    else:

        financial_data = extract_financial_metrics(
            indicators
        )


        latest_metrics = financial_data[
            "latest"
        ]


        annual_metrics = financial_data[
            "annual"
        ]


        latest_roe = latest_metrics.get(
            "roe"
        )

        latest_revenue_growth = (
            latest_metrics.get(
                "revenue_growth"
            )
        )

        latest_profit_growth = (
            latest_metrics.get(
                "profit_growth"
            )
        )

        latest_debt_ratio = (
            latest_metrics.get(
                "debt_ratio"
            )
        )


        # -------------------------------------------------
        # 长期投资核心值
        # -------------------------------------------------

        roe = annual_metrics.get(
            "roe"
        )

        revenue_growth = (
            annual_metrics.get(
                "revenue_growth"
            )
        )

        profit_growth = (
            annual_metrics.get(
                "profit_growth"
            )
        )

        debt_ratio = (
            annual_metrics.get(
                "debt_ratio"
            )
        )


        annual_eps = annual_metrics.get(
            "eps"
        )


        annual_bvps = annual_metrics.get(
            "bvps"
        )


        st.success(
            "✅ 财务指标获取成功"
        )


        # -------------------------------------------------
        # 最新报告期
        # -------------------------------------------------

        st.subheader(
            "🔵 最新报告期：近期经营状态"
        )


        a1, a2, a3, a4 = st.columns(4)


        a1.metric(
            "最新ROE",
            "暂无"
            if latest_roe is None
            else f"{latest_roe:.2f}%"
        )


        a2.metric(
            "最新营收增长",
            "暂无"
            if latest_revenue_growth is None
            else f"{latest_revenue_growth:.2f}%"
        )


        a3.metric(
            "最新净利润增长",
            "暂无"
            if latest_profit_growth is None
            else f"{latest_profit_growth:.2f}%"
        )


        a4.metric(
            "最新资产负债率",
            "暂无"
            if latest_debt_ratio is None
            else f"{latest_debt_ratio:.2f}%"
        )


        # -------------------------------------------------
        # 最近完整年度
        # -------------------------------------------------

        st.subheader(
            "🟢 最近完整年度：长期价值投资口径"
        )


        b1, b2, b3, b4 = st.columns(4)


        b1.metric(
            "年度ROE",
            "暂无"
            if roe is None
            else f"{roe:.2f}%"
        )


        b2.metric(
            "年度EPS",
            "暂无"
            if annual_eps is None
            else f"{annual_eps:.2f} 元"
        )


        b3.metric(
            "年度营收增长",
            "暂无"
            if revenue_growth is None
            else f"{revenue_growth:.2f}%"
        )


        b4.metric(
            "年度净利润增长",
            "暂无"
            if profit_growth is None
            else f"{profit_growth:.2f}%"
        )


        c5, c6 = st.columns(2)


        c5.metric(
            "年度资产负债率",
            "暂无"
            if debt_ratio is None
            else f"{debt_ratio:.2f}%"
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

    st.header(
        "💰 四、三张财务报表"
    )


    profit = get_profit_sheet(
        stock_code
    )


    balance = get_balance_sheet(
        stock_code
    )


    cashflow = get_cashflow_sheet(
        stock_code
    )


    report_metrics = extract_report_metrics(
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


    success_count = sum(
        x is not None
        for x in [
            profit,
            balance,
            cashflow
        ]
    )


    if success_count == 3:

        st.success(
            "✅ 三张财务报表全部获取成功"
        )

    elif success_count > 0:

        st.warning(
            f"⚠️ 三张报表获取 {success_count}/3"
        )

    else:

        st.error(
            "❌ 三张财务报表均未获取到"
        )


    with st.expander(
        "📋 查看原始财务报表"
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
    # 五、最近一期关键数据
    # =====================================================

    st.header(
        "💵 五、最近一期关键数据"
    )


    d1, d2, d3, d4, d5 = st.columns(5)


    d1.metric(
        "营业收入",
        "暂无"
        if latest_revenue is None
        else f"{latest_revenue / 1e8:.2f} 亿元"
    )


    d2.metric(
        "净利润",
        "暂无"
        if latest_profit is None
        else f"{latest_profit / 1e8:.2f} 亿元"
    )


    d3.metric(
        "经营现金流",
        "暂无"
        if latest_cashflow is None
        else f"{latest_cashflow / 1e8:.2f} 亿元"
    )


    d4.metric(
        "应收账款",
        "暂无"
        if latest_receivable is None
        else f"{latest_receivable / 1e8:.2f} 亿元"
    )


    d5.metric(
        "存货",
        "暂无"
        if latest_inventory is None
        else f"{latest_inventory / 1e8:.2f} 亿元"
    )


    # =====================================================
    # 六、财务排雷
    # =====================================================

    st.header(
        "🚨 六、财务排雷"
    )


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


    # -----------------------------------------------------
    # 风险评分
    # -----------------------------------------------------

    if (
        cash_profit_ratio is not None
        and cash_profit_ratio < 0.70
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
        roe is not None
        and roe < 10
    ):

        risk_score += 1

        risk_items.append(
            "长期ROE偏低"
        )


    if (
        debt_ratio is not None
        and debt_ratio >= 70
    ):

        risk_score += 2

        risk_items.append(
            "资产负债率偏高"
        )


    if risk_score == 0:

        st.success(
            "🟢 当前没有发现明显一级财务风险信号"
        )

    elif risk_score <= 2:

        st.warning(
            "🟡 当前存在少量需要观察的风险"
        )

    elif risk_score <= 4:

        st.warning(
            "🟠 当前存在多个风险信号"
        )

    else:

        st.error(
            "🔴 当前财务风险较高"
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

    st.divider()

    st.header(
        "⭐ 七、5年财务质量评分"
    )


    trend = financial_data.get(
        "trend",
        pd.DataFrame()
    )


    roe_values = []
    revenue_values = []
    profit_values = []
    debt_values = []


    if trend is not None and not trend.empty:

        st.dataframe(
            trend,
            use_container_width=True,
            hide_index=True
        )


        if "ROE" in trend.columns:

            roe_values = [
                safe_float(x)
                for x in trend["ROE"]
                if safe_float(x) is not None
            ]


        if "营收增长率" in trend.columns:

            revenue_values = [
                safe_float(x)
                for x in trend["营收增长率"]
                if safe_float(x) is not None
            ]


        if "净利润增长率" in trend.columns:

            profit_values = [
                safe_float(x)
                for x in trend["净利润增长率"]
                if safe_float(x) is not None
            ]


        if "资产负债率" in trend.columns:

            debt_values = [
                safe_float(x)
                for x in trend["资产负债率"]
                if safe_float(x) is not None
            ]


    # -----------------------------------------------------
    # ROE评分
    # -----------------------------------------------------

    roe_score = 0


    if roe_values:

        avg_roe = (
            sum(roe_values)
            / len(roe_values)
        )

        min_roe = min(
            roe_values
        )


        if (
            avg_roe >= 20
            and min_roe >= 15
        ):

            roe_score = 20

        elif (
            avg_roe >= 15
            and min_roe >= 10
        ):

            roe_score = 17

        elif avg_roe >= 10:

            roe_score = 13

        elif avg_roe >= 5:

            roe_score = 8

        else:

            roe_score = 3


    # -----------------------------------------------------
    # 营收成长
    # -----------------------------------------------------

    growth_score = 0


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


    # -----------------------------------------------------
    # 净利润成长
    # -----------------------------------------------------

    profit_score = 0


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


    # -----------------------------------------------------
    # 负债率
    # -----------------------------------------------------

    debt_score = 0


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


    # -----------------------------------------------------
    # 现金流
    # -----------------------------------------------------

    cash_score = 0


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
        roe_score
        + growth_score
        + profit_score
        + debt_score
        + cash_score
    )


    if financial_quality_score >= 85:

        financial_rating = "优秀"

    elif financial_quality_score >= 75:

        financial_rating = "良好"

    elif financial_quality_score >= 60:

        financial_rating = "一般"

    else:

        financial_rating = "偏弱"


    fs1, fs2 = st.columns(2)


    fs1.metric(
        "财务质量总分",
        f"{financial_quality_score} / 100"
    )


    fs2.metric(
        "评级",
        financial_rating
    )


    # =====================================================
    # 八、长期价值估值
    # =====================================================

    st.divider()

    st.header(
        "💰 八、长期价值估值 V12"
    )


    st.caption(
        "注意：这里明确使用最近完整年度EPS、BPS、ROE，"
        "不把单季度EPS和ROE直接用于长期估值。"
    )


    # -----------------------------------------------------
    # 基础数据
    # -----------------------------------------------------

    valuation_eps = annual_eps

    valuation_bvps = annual_bvps

    valuation_roe = roe


    e1, e2, e3, e4 = st.columns(4)


    e1.metric(
        "当前价格",
        "暂无"
        if valuation_price is None
        else f"{valuation_price:.2f} 元"
    )


    e2.metric(
        "年度EPS",
        "暂无"
        if valuation_eps is None
        else f"{valuation_eps:.2f} 元"
    )


    e3.metric(
        "年度ROE",
        "暂无"
        if valuation_roe is None
        else f"{valuation_roe:.2f}%"
    )


    e4.metric(
        "年度BPS",
        "暂无"
        if valuation_bvps is None
        else f"{valuation_bvps:.2f} 元"
    )


    # -----------------------------------------------------
    # 当前PE
    # -----------------------------------------------------

    if (
        valuation_price is not None
        and valuation_eps is not None
        and valuation_eps > 0
    ):

        current_pe = (
            valuation_price
            / valuation_eps
        )


    # -----------------------------------------------------
    # 当前PB
    # -----------------------------------------------------

    if (
        valuation_price is not None
        and valuation_bvps is not None
        and valuation_bvps > 0
    ):

        current_pb = (
            valuation_price
            / valuation_bvps
        )


    e5, e6 = st.columns(2)


    e5.metric(
        "当前PE（年度EPS）",
        "暂无"
        if current_pe is None
        else f"{current_pe:.2f} 倍"
    )


    e6.metric(
        "当前PB",
        "暂无"
        if current_pb is None
        else f"{current_pb:.2f} 倍"
    )


    # =====================================================
    # 九、目标PE
    # =====================================================

    st.subheader(
        "⚙️ 长期PE参数"
    )


    if valuation_roe is None:

        default_pe_conservative = 10.0
        default_pe_normal = 14.0
        default_pe_optimistic = 18.0


    elif valuation_roe >= 20:

        default_pe_conservative = 14.0
        default_pe_normal = 18.0
        default_pe_optimistic = 22.0


    elif valuation_roe >= 15:

        default_pe_conservative = 13.0
        default_pe_normal = 17.0
        default_pe_optimistic = 21.0


    elif valuation_roe >= 10:

        default_pe_conservative = 10.0
        default_pe_normal = 14.0
        default_pe_optimistic = 18.0


    else:

        default_pe_conservative = 8.0
        default_pe_normal = 11.0
        default_pe_optimistic = 14.0


    ep1, ep2, ep3 = st.columns(3)


    pe_conservative = ep1.number_input(
        "保守PE",
        min_value=3.0,
        max_value=50.0,
        value=float(
            default_pe_conservative
        ),
        step=1.0,
        key="v12_pe_c"
    )


    pe_normal = ep2.number_input(
        "中性PE",
        min_value=3.0,
        max_value=50.0,
        value=float(
            default_pe_normal
        ),
        step=1.0,
        key="v12_pe_n"
    )


    pe_optimistic = ep3.number_input(
        "乐观PE",
        min_value=3.0,
        max_value=50.0,
        value=float(
            default_pe_optimistic
        ),
        step=1.0,
        key="v12_pe_o"
    )


    # =====================================================
    # 十、目标PB
    # =====================================================

    st.subheader(
        "📚 长期PB参数"
    )


    bp1, bp2, bp3 = st.columns(3)


    pb_conservative = bp1.number_input(
        "保守PB",
        min_value=0.3,
        max_value=10.0,
        value=1.5,
        step=0.1,
        key="v12_pb_c"
    )


    pb_normal = bp2.number_input(
        "中性PB",
        min_value=0.3,
        max_value=10.0,
        value=2.0,
        step=0.1,
        key="v12_pb_n"
    )


    pb_optimistic = bp3.number_input(
        "乐观PB",
        min_value=0.3,
        max_value=10.0,
        value=2.5,
        step=0.1,
        key="v12_pb_o"
    )


    # =====================================================
    # 十一、PE估值
    # =====================================================

    pe_c_value = None
    pe_n_value = None
    pe_o_value = None


    if (
        valuation_eps is not None
        and valuation_eps > 0
    ):

        pe_c_value = (
            valuation_eps
            * pe_conservative
        )

        pe_n_value = (
            valuation_eps
            * pe_normal
        )

        pe_o_value = (
            valuation_eps
            * pe_optimistic
        )


    # =====================================================
    # 十二、PB估值
    # =====================================================

    pb_c_value = None
    pb_n_value = None
    pb_o_value = None


    if (
        valuation_bvps is not None
        and valuation_bvps > 0
    ):

        pb_c_value = (
            valuation_bvps
            * pb_conservative
        )

        pb_n_value = (
            valuation_bvps
            * pb_normal
        )

        pb_o_value = (
            valuation_bvps
            * pb_optimistic
        )


    # =====================================================
    # 十三、PE / PB 权重
    # =====================================================

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


    st.info(
        f"长期ROE："
        f"{valuation_roe:.2f}%"
        if valuation_roe is not None
        else "长期ROE暂无"
    )


    st.write(
        f"当前综合估值权重："
        f"PE {pe_weight:.0%} / "
        f"PB {pb_weight:.0%}"
    )


    # =====================================================
    # 十四、综合估值
    # =====================================================

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


        elif pe_value is not None:

            return pe_value


        elif pb_value is not None:

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


    # =====================================================
    # 十五、估值结果
    # =====================================================

    st.subheader(
        "🎯 三情景综合估值"
    )


    valuation_table = pd.DataFrame({

        "估值情景": [
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


    for column in [
        "PE估值",
        "PB估值",
        "综合估值"
    ]:

        valuation_table[column] = (
            valuation_table[column]
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
    # 十六、投资价格区间
    # =====================================================

    st.header(
        "💰 九、投资价格区间"
    )


    entry_price = None
    heavy_position_price = None
    high_valuation_price = None


    if normal_value is not None:

        # 建仓：
        # 合理价值打85折

        entry_price = (
            normal_value
            * 0.85
        )


        # 重仓：
        # 合理价值打70折

        heavy_position_price = (
            normal_value
            * 0.70
        )


    if optimistic_value is not None:

        high_valuation_price = (
            optimistic_value
        )


    p1, p2, p3, p4 = st.columns(4)


    p1.metric(
        "重仓参考价",
        "暂无"
        if heavy_position_price is None
        else f"{heavy_position_price:.2f} 元"
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
        if high_valuation_price is None
        else f"{high_valuation_price:.2f} 元"
    )


    # =====================================================
    # 十七、当前价格判断
    # =====================================================

    st.subheader(
        "🔍 当前价格判断"
    )


    valuation_gap = None


    if (
        valuation_price is not None
        and normal_value is not None
        and normal_value > 0
    ):

        valuation_gap = (
            normal_value
            / valuation_price
            - 1
        ) * 100


        st.metric(
            "相对中性合理价值空间",
            f"{valuation_gap:.2f}%"
        )


        if (
            heavy_position_price is not None
            and valuation_price <= heavy_position_price
        ):

            st.success(
                "🟢 当前价格进入重仓观察区"
            )


        elif (
            entry_price is not None
            and valuation_price <= entry_price
        ):

            st.success(
                "🟢 当前价格进入建仓观察区"
            )


        elif valuation_price <= normal_value:

            st.info(
                "🟡 当前价格低于合理价值，但安全边际一般"
            )


        elif (
            optimistic_value is not None
            and valuation_price <= optimistic_value
        ):

            st.warning(
                "🟠 当前价格高于中性合理价值，应等待更好的安全边际"
            )


        else:

            st.error(
                "🔴 当前价格高于乐观估值，估值风险偏高"
            )


    else:

        st.warning(
            "⚠️ 当前数据不足以完成估值判断"
        )


    # =====================================================
    # 十八、估值口径
    # =====================================================

    with st.expander(
        "📖 估值口径说明"
    ):

        st.write(
            "① 最新季度ROE：只用于观察近期经营状态。"
        )

        st.write(
            "② 最近完整年度ROE：用于长期价值投资评价。"
        )

        st.write(
            "③ 最近完整年度EPS：用于PE估值。"
        )

        st.write(
            "④ 最近完整年度BPS：用于PB估值。"
        )

        st.write(
            "⑤ PE/PB综合估值只是模型参考，不等于未来股价预测。"
        )

        st.write(
            "⑥ 重仓价/建仓价属于安全边际价格，不是绝对合理价格。"
        )


    # =====================================================
    # 十九、综合投资评级
    # =====================================================

    st.divider()

    st.header(
        "🏆 十、ValueStock AI 综合投资评级"
    )


    # -----------------------------------------------------
    # 财务质量 30分
    # -----------------------------------------------------

    financial_component = (
        financial_quality_score
        * 0.30
    )


    # -----------------------------------------------------
    # 成长性 20分
    # -----------------------------------------------------

    growth_component = 0


    if (
        revenue_growth is not None
        and profit_growth is not None
    ):

        growth_avg = (
            revenue_growth
            + profit_growth
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


    # -----------------------------------------------------
    # 盈利能力15分
    # -----------------------------------------------------

    profitability_component = 0


    if roe is not None:

        if roe >= 20:

            profitability_component = 15

        elif roe >= 15:

            profitability_component = 13

        elif roe >= 10:

            profitability_component = 10

        elif roe >= 5:

            profitability_component = 6

        else:

            profitability_component = 2


    # -----------------------------------------------------
    # 现金流15分
    # -----------------------------------------------------

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

        else:

            cash_component = 0


    # -----------------------------------------------------
    # 财务安全10分
    # -----------------------------------------------------

    safety_component = 0


    if debt_ratio is not None:

        if debt_ratio < 40:

            safety_component = 10

        elif debt_ratio < 50:

            safety_component = 9

        elif debt_ratio < 60:

            safety_component = 7

        elif debt_ratio < 70:

            safety_component = 5

        else:

            safety_component = 2


    # -----------------------------------------------------
    # 估值10分
    # -----------------------------------------------------

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

        else:

            valuation_component = 0


    # -----------------------------------------------------
    # 风险扣分
    # -----------------------------------------------------

    if risk_score >= 6:

        risk_penalty = 12

    elif risk_score >= 4:

        risk_penalty = 8

    elif risk_score >= 2:

        risk_penalty = 4

    else:

        risk_penalty = 0


    # -----------------------------------------------------
    # 最终评分
    # -----------------------------------------------------

    raw_score = (
        financial_component
        + growth_component
        + profitability_component
        + cash_component
        + safety_component
        + valuation_component
    )


    final_score = round(
        max(
            0,
            min(
                100,
                raw_score
                - risk_penalty
            )
        )
    )


    # -----------------------------------------------------
    # 评级
    # -----------------------------------------------------

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


    rr1, rr2 = st.columns(2)


    rr1.metric(
        "ValueStock AI综合分",
        f"{final_score} / 100"
    )


    rr2.metric(
        "投资评级",
        final_rating
    )


    # =====================================================
    # 二十分项评分表
    # =====================================================

    st.subheader(
        "📊 综合评分构成"
    )


    component_table = pd.DataFrame({

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

            round(
                financial_component,
                1
            ),

            growth_component,

            profitability_component,

            cash_component,

            safety_component,

            valuation_component

        ]

    })


    st.dataframe(
        component_table,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # 二十一、最终投资结论
    # =====================================================

    st.subheader(
        "🏆 十一、最终投资结论"
    )


    if final_score >= 85:

        conclusion = (
            "公司当前综合质量优秀，"
            "具备进入长期价值投资重点候选池的条件。"
        )


    elif final_score >= 75:

        conclusion = (
            "公司综合质量较好，"
            "值得长期跟踪，重点等待合适估值。"
        )


    elif final_score >= 65:

        conclusion = (
            "公司具备一定投资价值，"
            "但仍有多个维度需要验证。"
        )


    elif final_score >= 50:

        conclusion = (
            "公司存在一定风险，"
            "当前不适合重仓。"
        )


    else:

        conclusion = (
            "当前综合质量偏弱，"
            "暂不建议作为长期核心资产。"
        )


    if (
        valuation_price is not None
        and heavy_position_price is not None
        and valuation_price <= heavy_position_price
    ):

        conclusion += (
            " 当前价格已进入模型重仓观察区。"
        )


    elif (
        valuation_price is not None
        and entry_price is not None
        and valuation_price <= entry_price
    ):

        conclusion += (
            " 当前价格已进入模型建仓观察区。"
        )


    elif (
        valuation_price is not None
        and normal_value is not None
        and valuation_price <= normal_value
    ):

        conclusion += (
            " 当前价格低于模型合理价值，但安全边际一般。"
        )


    elif (
        valuation_price is not None
        and normal_value is not None
        and valuation_price > normal_value
    ):

        conclusion += (
            " 当前价格高于模型中性合理价值，应控制估值风险。"
        )


    st.info(
        conclusion
    )


    # =====================================================
    # 二十二、数据完整度
    # =====================================================

    st.subheader(
        "📌 十二、数据完整度"
    )


    checks = [

        valuation_price is not None,

        latest_roe is not None,

        latest_revenue_growth is not None,

        latest_profit_growth is not None,

        latest_debt_ratio is not None,

        annual_eps is not None,

        annual_bvps is not None,

        roe is not None,

        latest_revenue is not None,

        latest_profit is not None,

        latest_cashflow is not None

    ]


    available = sum(
        1
        for x in checks
        if x
    )


    total = len(checks)


    completeness = (
        available
        / total
        * 100
    )


    st.progress(
        completeness / 100
    )


    st.write(
        f"当前关键数据完整度："
        f"{completeness:.0f}% "
        f"（{available}/{total}）"
    )


    # =====================================================
    # 二十三、数据诊断
    # =====================================================

    st.subheader(
        "🛠️ 十三、接口诊断"
    )


    diagnostic = pd.DataFrame({

        "数据项目": [

            "实时行情",
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
            "中性合理价",
            "建仓价",
            "重仓价"

        ],

        "状态": [

            "✅ 成功"
            if valuation_price is not None
            else "❌ 无数据",

            "✅ 成功"
            if history is not None
            else "❌ 无数据",

            "✅ 成功"
            if indicators is not None
            else "❌ 无数据",

            "✅ 成功"
            if latest_roe is not None
            else "❌ 无数据",

            "✅ 成功"
            if roe is not None
            else "❌ 无数据",

            "✅ 成功"
            if annual_eps is not None
            else "❌ 无数据",

            "✅ 成功"
            if annual_bvps is not None
            else "❌ 无数据",

            "✅ 成功"
            if profit is not None
            else "❌ 无数据",

            "✅ 成功"
            if balance is not None
            else "❌ 无数据",

            "✅ 成功"
            if cashflow is not None
            else "❌ 无数据",

            "✅ 成功"
            if latest_cashflow is not None
            else "❌ 无数据",

            "✅ 成功"
            if current_pe is not None
            else "❌ 无数据",

            "✅ 成功"
            if current_pb is not None
            else "❌ 无数据",

            "✅ 成功"
            if normal_value is not None
            else "❌ 无数据",

            "✅ 成功"
            if entry_price is not None
            else "❌ 无数据",

            "✅ 成功"
            if heavy_position_price is not None
            else "❌ 无数据"

        ]

    })


    st.dataframe(
        diagnostic,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # 二十四、最终说明
    # =====================================================

    st.divider()

    st.caption(
        "ValueStock AI V12："
        "最新季度用于观察经营状态；"
        "最近完整年度用于长期价值投资与估值；"
        "PE/PB用于估值敏感性分析；"
        "重仓价/建仓价用于安全边际判断。"
    )
