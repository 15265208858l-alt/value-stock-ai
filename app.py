import streamlit as st
import akshare as ak
import pandas as pd
import math

# =========================================================
# 页面设置
# =========================================================

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("A股长期价值投资分析 V11")
st.caption("实时价格 + 核心财务指标 + 5年质量 + 财务排雷 + PE/PB估值 + 投资价格区间")

st.divider()


# =========================================================
# 一、基础工具函数
# =========================================================

def clean_code(stock_code):
    """清理股票代码"""

    if stock_code is None:
        return ""

    stock_code = str(stock_code).strip()

    if len(stock_code) != 6 or not stock_code.isdigit():
        return ""

    return stock_code


def get_market_code(stock_code):
    """转换为 sh600000 / sz000001"""

    if stock_code.startswith(("6", "68")):
        return "sh" + stock_code

    if stock_code.startswith(("0", "3")):
        return "sz" + stock_code

    if stock_code.startswith(("4", "8")):
        return "bj" + stock_code

    return stock_code


def get_em_symbol(stock_code):
    """转换为 600519.SH / 000001.SZ"""

    if stock_code.startswith(("6", "68")):
        return stock_code + ".SH"

    if stock_code.startswith(("0", "3")):
        return stock_code + ".SZ"

    if stock_code.startswith(("4", "8")):
        return stock_code + ".BJ"

    return stock_code


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
            "nan",
            "NaN",
            "None",
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
    """从 DataFrame 中寻找字段"""

    if df is None or df.empty:
        return None

    for col in candidates:

        if col in df.columns:
            return col

    return None


def latest_valid_value(df, col):
    """从指定字段中寻找最近一个有效数字"""

    if df is None or df.empty or col is None:
        return None

    for value in df[col]:

        number = safe_float(value)

        if number is not None:
            return number

    return None


def sort_by_report_date(df):
    """按报告日期从新到旧排序"""

    if df is None or df.empty:
        return df

    result = df.copy()

    date_col = find_column(
        result,
        [
            "REPORT_DATE",
            "报告日",
            "报告日期",
            "日期",
            "报告期",
            "截止日期"
        ]
    )

    if date_col:

        result["_排序日期"] = pd.to_datetime(
            result[date_col],
            errors="coerce"
        )

        result = (
            result
            .sort_values(
                "_排序日期",
                ascending=False
            )
            .drop(columns=["_排序日期"])
        )

    return result.reset_index(drop=True)


def safe_ratio(a, b):

    if a is None or b is None:
        return None

    if b == 0:
        return None

    return a / b


# =========================================================
# 二、实时行情
# =========================================================

@st.cache_data(ttl=60)
def get_realtime_data(stock_code):

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
            df[code_col].astype(str) == stock_code
        ]

        if result.empty:
            return None

        return result.iloc[0].to_dict()

    except Exception:

        return None


# =========================================================
# 三、历史行情
# =========================================================

@st.cache_data(ttl=300)
def get_history_data(stock_code):

    market_code = get_market_code(stock_code)

    try:

        # 优先新版东方财富历史行情
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


        # 再尝试腾讯
        try:

            data = ak.stock_zh_a_hist_tx(
                symbol=market_code,
                start_date="20200101",
                end_date="20500101",
                adjust=""
            )

            if data is not None and not data.empty:
                return data

        except Exception:
            pass

        return None

    except Exception:
        return None


# =========================================================
# 四、财务指标
# =========================================================

@st.cache_data(ttl=3600)
def get_financial_indicators(stock_code):

    em_symbol = get_em_symbol(stock_code)

    # -----------------------------------------------------
    # 优先东方财富
    # -----------------------------------------------------

    try:

        data = ak.stock_financial_analysis_indicator_em(
            symbol=em_symbol,
            indicator="按报告期"
        )

        if data is not None and not data.empty:

            return sort_by_report_date(data), "东方财富"

    except Exception:
        pass


    # -----------------------------------------------------
    # 新浪兜底
    # -----------------------------------------------------

    try:

        data = ak.stock_financial_analysis_indicator(
            symbol=stock_code
        )

        if data is not None and not data.empty:

            return sort_by_report_date(data), "新浪"

    except Exception:
        pass


    return None, None


# =========================================================
# 五、财务报表
# =========================================================

@st.cache_data(ttl=3600)
def get_financial_report(stock_code, report_type):

    market_code = get_market_code(stock_code)

    try:

        data = ak.stock_financial_report_sina(
            stock=market_code,
            symbol=report_type
        )

        if data is None or data.empty:
            return None

        return sort_by_report_date(data)

    except Exception:

        return None


# =========================================================
# 六、提取财务核心指标
# =========================================================

def extract_core_metrics(indicators):

    result = {
        "roe": None,
        "revenue_growth": None,
        "profit_growth": None,
        "debt_ratio": None,
        "eps": None,
        "bvps": None,
        "operating_cash_per_share": None,
        "period": None
    }

    if indicators is None or indicators.empty:
        return result

    latest = indicators.iloc[0]

    # -----------------------------------------------------
    # ROE
    # -----------------------------------------------------

    roe_col = find_column(
        indicators,
        [
            "ROEJQ",
            "加权净资产收益率(%)",
            "加权净资产收益率",
            "净资产收益率(%)",
            "净资产收益率"
        ]
    )

    # -----------------------------------------------------
    # 营收增长
    # -----------------------------------------------------

    revenue_growth_col = find_column(
        indicators,
        [
            "TOTALOPERATEREVETZ",
            "主营业务收入增长率(%)",
            "主营业务收入增长率",
            "营业收入增长率(%)",
            "营业收入增长率"
        ]
    )

    # -----------------------------------------------------
    # 净利润增长
    # -----------------------------------------------------

    profit_growth_col = find_column(
        indicators,
        [
            "PARENTNETPROFITTZ",
            "净利润增长率(%)",
            "净利润增长率",
            "归属净利润同比增长(%)"
        ]
    )

    # -----------------------------------------------------
    # 负债率
    # -----------------------------------------------------

    debt_col = find_column(
        indicators,
        [
            "ZCFZL",
            "资产负债率(%)",
            "资产负债率"
        ]
    )

    # -----------------------------------------------------
    # EPS
    # -----------------------------------------------------

    eps_col = find_column(
        indicators,
        [
            "EPSJB",
            "摊薄每股收益(元)",
            "基本每股收益(元)",
            "基本每股收益",
            "每股收益(元)",
            "每股收益"
        ]
    )

    # -----------------------------------------------------
    # BPS
    # -----------------------------------------------------

    bvps_col = find_column(
        indicators,
        [
            "BPS",
            "每股净资产(元)",
            "每股净资产",
            "每股净资产_调整后(元)",
            "每股净资产_调整前(元)"
        ]
    )

    # -----------------------------------------------------
    # 每股经营现金流
    # -----------------------------------------------------

    cash_per_share_col = find_column(
        indicators,
        [
            "MGJYXJJE",
            "每股经营性现金流(元)",
            "每股经营性现金流"
        ]
    )

    # -----------------------------------------------------
    # 报告期
    # -----------------------------------------------------

    period_col = find_column(
        indicators,
        [
            "REPORT_DATE",
            "日期",
            "报告期",
            "报告日期"
        ]
    )

    # -----------------------------------------------------
    # 提取
    # -----------------------------------------------------

    if roe_col:
        result["roe"] = safe_float(latest[roe_col])

    if revenue_growth_col:
        result["revenue_growth"] = safe_float(
            latest[revenue_growth_col]
        )

    if profit_growth_col:
        result["profit_growth"] = safe_float(
            latest[profit_growth_col]
        )

    if debt_col:
        result["debt_ratio"] = safe_float(
            latest[debt_col]
        )

    if eps_col:
        result["eps"] = safe_float(
            latest[eps_col]
        )

    if bvps_col:
        result["bvps"] = safe_float(
            latest[bvps_col]
        )

    if cash_per_share_col:
        result["operating_cash_per_share"] = safe_float(
            latest[cash_per_share_col]
        )

    if period_col:
        result["period"] = str(
            latest[period_col]
        )

    return result


# =========================================================
# 七、报表核心数据提取
# =========================================================

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

    # -----------------------------------------------------
    # 利润表
    # -----------------------------------------------------

    revenue_col = find_column(
        profit,
        [
            "营业总收入",
            "营业收入",
            "一、营业总收入"
        ]
    )

    net_profit_col = find_column(
        profit,
        [
            "归属于母公司所有者的净利润",
            "归属于母公司股东的净利润",
            "净利润",
            "五、净利润"
        ]
    )

    # -----------------------------------------------------
    # 资产负债表
    # -----------------------------------------------------

    receivable_col = find_column(
        balance,
        [
            "应收账款",
            "应收款项"
        ]
    )

    inventory_col = find_column(
        balance,
        [
            "存货"
        ]
    )

    # -----------------------------------------------------
    # 现金流量表
    # -----------------------------------------------------

    operating_cash_col = find_column(
        cashflow,
        [
            "经营活动产生的现金流量净额",
            "经营活动现金流量净额"
        ]
    )

    # -----------------------------------------------------
    # 最新一期
    # -----------------------------------------------------

    if profit is not None and not profit.empty:

        profit = sort_by_report_date(profit)

        if revenue_col:
            result["revenue"] = safe_float(
                profit.iloc[0][revenue_col]
            )

        if net_profit_col:
            result["net_profit"] = safe_float(
                profit.iloc[0][net_profit_col]
            )

    if balance is not None and not balance.empty:

        balance = sort_by_report_date(balance)

        if receivable_col:
            result["receivable"] = safe_float(
                balance.iloc[0][receivable_col]
            )

        if inventory_col:
            result["inventory"] = safe_float(
                balance.iloc[0][inventory_col]
            )

    if cashflow is not None and not cashflow.empty:

        cashflow = sort_by_report_date(cashflow)

        if operating_cash_col:
            result["operating_cashflow"] = safe_float(
                cashflow.iloc[0][operating_cash_col]
            )

    return result


# =========================================================
# 八、输入股票
# =========================================================

stock_code_input = st.text_input(
    "请输入A股股票代码",
    placeholder="例如：600089、000333、601899"
)


start_analysis = st.button(
    "🚀 开始价值投资分析",
    type="primary"
)


# =========================================================
# 九、默认变量
# =========================================================

history = None
spot = None
indicators = None

profit = None
balance = None
cashflow = None

indicator_source = None

roe = None
revenue_growth = None
profit_growth = None
debt_ratio = None
latest_eps = None
latest_bvps = None

latest_revenue = None
latest_profit = None
latest_receivable = None
latest_inventory = None
latest_cashflow = None

cash_profit_ratio = None
receivable_ratio = None
inventory_ratio = None

financial_quality_score = 0
financial_rating = "数据不足"

valuation_price = None
current_pe = None
current_pb = None

conservative_value = None
normal_value = None
optimistic_value = None

entry_price = None
heavy_position_price = None
high_valuation_price = None

risk_score = 0
risk_items = []


# =========================================================
# 十、开始分析
# =========================================================

if start_analysis:

    stock_code = clean_code(
        stock_code_input
    )

    if not stock_code:

        st.error(
            "❌ 股票代码必须是6位数字，例如：600089"
        )

        st.stop()


    st.info(
        f"正在分析 {stock_code}，请稍候……"
    )


    # =====================================================
    # A. 实时行情
    # =====================================================

    st.header("📌 一、实时行情")

    try:

        spot = get_realtime_data(
            stock_code
        )

        if spot is not None:

            current_price_col = "最新价"

            valuation_price = safe_float(
                spot.get(current_price_col)
            )

            spot_name = spot.get(
                "名称",
                ""
            )

            spot_change = safe_float(
                spot.get("涨跌幅")
            )

            spot_pe = safe_float(
                spot.get("市盈率-动态")
            )

            spot_pb = safe_float(
                spot.get("市净率")
            )


            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "股票名称",
                str(spot_name)
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
                if spot_change is None
                else f"{spot_change:.2f}%"
            )

            c4.metric(
                "动态PE",
                "暂无"
                if spot_pe is None
                else f"{spot_pe:.2f}"
            )

            if spot_pb is not None:
                current_pb = spot_pb

            st.success(
                "✅ 实时行情获取成功"
            )

        else:

            st.warning(
                "⚠️ 实时行情暂未获取成功，将继续尝试历史行情。"
            )

    except Exception as e:

        st.warning(
            "⚠️ 实时行情接口异常："
            + str(e)
        )


    # =====================================================
    # B. 历史行情
    # =====================================================

    try:

        history = get_history_data(
            stock_code
        )

        if history is not None and not history.empty:

            st.success(
                "✅ 历史行情获取成功"
            )

            with st.expander(
                "📈 查看最近行情"
            ):

                st.dataframe(
                    history.tail(10),
                    use_container_width=True,
                    hide_index=True
                )

    except Exception as e:

        st.warning(
            "⚠️ 历史行情获取失败："
            + str(e)
        )


    # =====================================================
    # C. 财务指标
    # =====================================================

    st.divider()

    st.header("📊 二、当前核心财务指标")

    try:

        indicators, indicator_source = (
            get_financial_indicators(
                stock_code
            )
        )

        if indicators is None or indicators.empty:

            st.error(
                "❌ 财务指标仍未获取到。"
            )

        else:

            core = extract_core_metrics(
                indicators
            )

            roe = core["roe"]
            revenue_growth = core["revenue_growth"]
            profit_growth = core["profit_growth"]
            debt_ratio = core["debt_ratio"]
            latest_eps = core["eps"]
            latest_bvps = core["bvps"]


            st.success(
                f"✅ 财务指标获取成功，数据源：{indicator_source}"
            )


            # -------------------------------------------------
            # 核心指标
            # -------------------------------------------------

            m1, m2, m3, m4 = st.columns(4)

            m1.metric(
                "ROE",
                "暂无"
                if roe is None
                else f"{roe:.2f}%"
            )

            m2.metric(
                "营收增长率",
                "暂无"
                if revenue_growth is None
                else f"{revenue_growth:.2f}%"
            )

            m3.metric(
                "净利润增长率",
                "暂无"
                if profit_growth is None
                else f"{profit_growth:.2f}%"
            )

            m4.metric(
                "资产负债率",
                "暂无"
                if debt_ratio is None
                else f"{debt_ratio:.2f}%"
            )


            m5, m6, m7 = st.columns(3)

            m5.metric(
                "EPS",
                "暂无"
                if latest_eps is None
                else f"{latest_eps:.2f} 元"
            )

            m6.metric(
                "每股净资产",
                "暂无"
                if latest_bvps is None
                else f"{latest_bvps:.2f} 元"
            )

            m7.metric(
                "报告期",
                str(core["period"])
                if core["period"]
                else "暂无"
            )


    except Exception as e:

        st.error(
            "❌ 核心财务指标分析失败"
        )

        st.code(
            str(e)
        )


    # =====================================================
    # D. 三张财务报表
    # =====================================================

    st.divider()

    st.header("💰 三、三张财务报表")

    try:

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


        st.success(
            "✅ 三张财务报表获取完成"
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


    except Exception as e:

        st.warning(
            "⚠️ 三张财务报表部分获取失败"
        )

        st.code(
            str(e)
        )


    # =====================================================
    # E. 最近一期关键数据
    # =====================================================

    st.header("💵 四、最近一期关键财务数据")

    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric(
        "营业收入",
        "暂无"
        if latest_revenue is None
        else f"{latest_revenue / 1e8:.2f} 亿元"
    )

    k2.metric(
        "净利润",
        "暂无"
        if latest_profit is None
        else f"{latest_profit / 1e8:.2f} 亿元"
    )

    k3.metric(
        "经营现金流",
        "暂无"
        if latest_cashflow is None
        else f"{latest_cashflow / 1e8:.2f} 亿元"
    )

    k4.metric(
        "应收账款",
        "暂无"
        if latest_receivable is None
        else f"{latest_receivable / 1e8:.2f} 亿元"
    )

    k5.metric(
        "存货",
        "暂无"
        if latest_inventory is None
        else f"{latest_inventory / 1e8:.2f} 亿元"
    )


    # =====================================================
    # F. 利润质量
    # =====================================================

    st.header("🔎 五、利润质量与财务排雷")

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


    q1, q2, q3 = st.columns(3)

    q1.metric(
        "经营现金流 / 净利润",
        "暂无"
        if cash_profit_ratio is None
        else f"{cash_profit_ratio:.2f}"
    )

    q2.metric(
        "应收账款 / 营收",
        "暂无"
        if receivable_ratio is None
        else f"{receivable_ratio:.2%}"
    )

    q3.metric(
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


    if roe is not None and roe < 10:

        risk_score += 1

        risk_items.append(
            "ROE偏低"
        )


    if debt_ratio is not None and debt_ratio >= 70:

        risk_score += 2

        risk_items.append(
            "资产负债率偏高"
        )


    if risk_score == 0:

        st.success(
            "🟢 暂未发现明显的一级财务风险。"
        )

    elif risk_score <= 2:

        st.warning(
            "🟡 存在少量需要观察的风险信号。"
        )

    elif risk_score <= 4:

        st.warning(
            "🟠 存在多个值得深入研究的风险信号。"
        )

    else:

        st.error(
            "🔴 财务风险信号较多，需要谨慎。"
        )


    if risk_items:

        st.write("### ⚠️ 重点关注")

        for item in risk_items:

            st.write(
                f"- {item}"
            )


    # =====================================================
    # G. 5年财务质量
    # =====================================================

    st.divider()

    st.header("⭐ 六、5年财务质量评分")


    trend = indicators.copy()

    if trend is not None and not trend.empty:

        date_col = find_column(
            trend,
            [
                "REPORT_DATE",
                "日期",
                "报告期",
                "报告日期"
            ]
        )

        if date_col:

            trend["_date"] = pd.to_datetime(
                trend[date_col],
                errors="coerce"
            )

            trend = trend.dropna(
                subset=["_date"]
            )

            trend["年份"] = (
                trend["_date"].dt.year
            )

            trend = (
                trend
                .sort_values("_date")
                .groupby("年份")
                .tail(1)
                .sort_values("_date")
                .tail(5)
            )

        else:

            trend = trend.head(5)


        roe_values = []

        revenue_values = []

        profit_values = []

        debt_values = []

        roe_col_v8 = find_column(
            trend,
            [
                "ROEJQ",
                "加权净资产收益率(%)",
                "加权净资产收益率"
            ]
        )

        revenue_col_v8 = find_column(
            trend,
            [
                "TOTALOPERATEREVETZ",
                "主营业务收入增长率(%)",
                "主营业务收入增长率"
            ]
        )

        profit_col_v8 = find_column(
            trend,
            [
                "PARENTNETPROFITTZ",
                "净利润增长率(%)",
                "净利润增长率"
            ]
        )

        debt_col_v8 = find_column(
            trend,
            [
                "ZCFZL",
                "资产负债率(%)",
                "资产负债率"
            ]
        )


        if roe_col_v8:

            roe_values = [
                safe_float(x)
                for x in trend[roe_col_v8]
                if safe_float(x) is not None
            ]


        if revenue_col_v8:

            revenue_values = [
                safe_float(x)
                for x in trend[revenue_col_v8]
                if safe_float(x) is not None
            ]


        if profit_col_v8:

            profit_values = [
                safe_float(x)
                for x in trend[profit_col_v8]
                if safe_float(x) is not None
            ]


        if debt_col_v8:

            debt_values = [
                safe_float(x)
                for x in trend[debt_col_v8]
                if safe_float(x) is not None
            ]


        # -------------------------------------------------
        # 展示5年趋势
        # -------------------------------------------------

        display_data = {}

        if "年份" in trend.columns:
            display_data["年份"] = trend["年份"]

        if roe_col_v8:
            display_data["ROE"] = trend[roe_col_v8]

        if revenue_col_v8:
            display_data["营收增长率"] = trend[
                revenue_col_v8
            ]

        if profit_col_v8:
            display_data["净利润增长率"] = trend[
                profit_col_v8
            ]

        if debt_col_v8:
            display_data["资产负债率"] = trend[
                debt_col_v8
            ]


        if display_data:

            st.dataframe(
                pd.DataFrame(display_data),
                use_container_width=True,
                hide_index=True
            )


        # -------------------------------------------------
        # 5年评分
        # -------------------------------------------------

        roe_score = 0
        growth_score = 0
        profit_score = 0
        debt_score = 0


        if roe_values:

            avg_roe = sum(roe_values) / len(roe_values)

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

            if avg_growth >= 15 and positive_years >= 4:
                growth_score = 20

            elif avg_growth >= 8 and positive_years >= 4:
                growth_score = 16

            elif avg_growth >= 0:
                growth_score = 11

            else:
                growth_score = 4


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


        financial_quality_score = (
            roe_score
            + growth_score
            + profit_score
            + debt_score
            + cash_score
        )


        financial_quality_score = min(
            financial_quality_score,
            100
        )


        if financial_quality_score >= 85:
            financial_rating = "优秀"

        elif financial_quality_score >= 75:
            financial_rating = "良好"

        elif financial_quality_score >= 60:
            financial_rating = "一般"

        else:
            financial_rating = "偏弱"


        s1, s2 = st.columns(2)

        s1.metric(
            "财务质量总分",
            f"{financial_quality_score} / 100"
        )

        s2.metric(
            "综合评级",
            financial_rating
        )


    # =====================================================
    # H. V11估值系统
    # =====================================================

    st.divider()

    st.header("💰 七、V11价值估值系统")

    st.caption(
        "优先采用EPS与BPS进行PE/PB综合估值；如果某一项数据缺失，系统自动使用剩余有效估值方法，不再整组显示“暂无”。"
    )


    # -----------------------------------------------------
    # 当前PE / PB
    # -----------------------------------------------------

    if (
        valuation_price is not None
        and latest_eps is not None
        and latest_eps > 0
    ):

        current_pe = (
            valuation_price
            / latest_eps
        )


    if (
        valuation_price is not None
        and latest_bvps is not None
        and latest_bvps > 0
    ):

        current_pb = (
            valuation_price
            / latest_bvps
        )


    e1, e2, e3, e4 = st.columns(4)

    e1.metric(
        "当前价格",
        "暂无"
        if valuation_price is None
        else f"{valuation_price:.2f} 元"
    )

    e2.metric(
        "EPS",
        "暂无"
        if latest_eps is None
        else f"{latest_eps:.2f} 元"
    )

    e3.metric(
        "当前PE",
        "暂无"
        if current_pe is None
        else f"{current_pe:.2f}"
    )

    e4.metric(
        "当前PB",
        "暂无"
        if current_pb is None
        else f"{current_pb:.2f}"
    )


    # -----------------------------------------------------
    # 自动目标PE
    # -----------------------------------------------------

    if roe is not None:

        if roe >= 20:

            default_pe_conservative = 15.0
            default_pe_normal = 20.0
            default_pe_optimistic = 25.0

        elif roe >= 15:

            default_pe_conservative = 13.0
            default_pe_normal = 17.0
            default_pe_optimistic = 22.0

        elif roe >= 10:

            default_pe_conservative = 10.0
            default_pe_normal = 14.0
            default_pe_optimistic = 18.0

        else:

            default_pe_conservative = 8.0
            default_pe_normal = 11.0
            default_pe_optimistic = 15.0

    else:

        default_pe_conservative = 10.0
        default_pe_normal = 14.0
        default_pe_optimistic = 18.0


    st.subheader("⚙️ 估值参数")


    pe1, pe2, pe3 = st.columns(3)


    pe_conservative = pe1.number_input(
        "保守目标PE",
        min_value=1.0,
        max_value=100.0,
        value=float(default_pe_conservative),
        step=1.0
    )


    pe_normal = pe2.number_input(
        "中性目标PE",
        min_value=1.0,
        max_value=100.0,
        value=float(default_pe_normal),
        step=1.0
    )


    pe_optimistic = pe3.number_input(
        "乐观目标PE",
        min_value=1.0,
        max_value=100.0,
        value=float(default_pe_optimistic),
        step=1.0
    )


    pb1, pb2, pb3 = st.columns(3)


    pb_conservative = pb1.number_input(
        "保守目标PB",
        min_value=0.1,
        max_value=20.0,
        value=1.2,
        step=0.1
    )


    pb_normal = pb2.number_input(
        "中性目标PB",
        min_value=0.1,
        max_value=20.0,
        value=1.8,
        step=0.1
    )


    pb_optimistic = pb3.number_input(
        "乐观目标PB",
        min_value=0.1,
        max_value=20.0,
        value=2.5,
        step=0.1
    )


    # =====================================================
    # PE估值
    # =====================================================

    pe_conservative_value = None
    pe_normal_value = None
    pe_optimistic_value = None


    if latest_eps is not None and latest_eps > 0:

        pe_conservative_value = (
            latest_eps
            * pe_conservative
        )

        pe_normal_value = (
            latest_eps
            * pe_normal
        )

        pe_optimistic_value = (
            latest_eps
            * pe_optimistic
        )


    # =====================================================
    # PB估值
    # =====================================================

    pb_conservative_value = None
    pb_normal_value = None
    pb_optimistic_value = None


    if latest_bvps is not None and latest_bvps > 0:

        pb_conservative_value = (
            latest_bvps
            * pb_conservative
        )

        pb_normal_value = (
            latest_bvps
            * pb_normal
        )

        pb_optimistic_value = (
            latest_bvps
            * pb_optimistic
        )


    # =====================================================
    # 综合估值
    # =====================================================

    if roe is not None and roe >= 15:

        pe_weight = 0.70
        pb_weight = 0.30

    elif roe is not None and roe >= 10:

        pe_weight = 0.60
        pb_weight = 0.40

    else:

        pe_weight = 0.50
        pb_weight = 0.50


    # -----------------------------------------------------
    # 保守
    # -----------------------------------------------------

    if (
        pe_conservative_value is not None
        and pb_conservative_value is not None
    ):

        conservative_value = (
            pe_conservative_value * pe_weight
            + pb_conservative_value * pb_weight
        )

    elif pe_conservative_value is not None:

        conservative_value = (
            pe_conservative_value
        )

    elif pb_conservative_value is not None:

        conservative_value = (
            pb_conservative_value
        )


    # -----------------------------------------------------
    # 中性
    # -----------------------------------------------------

    if (
        pe_normal_value is not None
        and pb_normal_value is not None
    ):

        normal_value = (
            pe_normal_value * pe_weight
            + pb_normal_value * pb_weight
        )

    elif pe_normal_value is not None:

        normal_value = pe_normal_value

    elif pb_normal_value is not None:

        normal_value = pb_normal_value


    # -----------------------------------------------------
    # 乐观
    # -----------------------------------------------------

    if (
        pe_optimistic_value is not None
        and pb_optimistic_value is not None
    ):

        optimistic_value = (
            pe_optimistic_value * pe_weight
            + pb_optimistic_value * pb_weight
        )

    elif pe_optimistic_value is not None:

        optimistic_value = pe_optimistic_value

    elif pb_optimistic_value is not None:

        optimistic_value = pb_optimistic_value


    # =====================================================
    # 估值表
    # =====================================================

    valuation_table = pd.DataFrame({

        "情景": [
            "保守",
            "中性",
            "乐观"
        ],

        "综合估值": [
            conservative_value,
            normal_value,
            optimistic_value
        ]

    })


    valuation_table["综合估值"] = (
        valuation_table["综合估值"]
        .apply(
            lambda x:
            "暂无"
            if x is None
            else f"{x:.2f} 元"
        )
    )


    st.subheader(
        "🎯 三种情景估值"
    )


    st.dataframe(
        valuation_table,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # I. 投资价格区间
    # =====================================================

    st.divider()

    st.header("💰 八、投资价格区间")


    # -----------------------------------------------------
    # 核心价格
    # -----------------------------------------------------

    if normal_value is not None:

        entry_price = (
            normal_value
            * 0.85
        )

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


    # -----------------------------------------------------
    # 价格表
    # -----------------------------------------------------

    price_table = pd.DataFrame({

        "价格类型": [
            "重仓区",
            "建仓区",
            "合理价值",
            "高估参考"
        ],

        "参考价格": [
            heavy_position_price,
            entry_price,
            normal_value,
            high_valuation_price
        ]

    })


    price_table["参考价格"] = (
        price_table["参考价格"]
        .apply(
            lambda x:
            "暂无"
            if x is None
            else f"{x:.2f} 元"
        )
    )


    st.dataframe(
        price_table,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # J. 当前价格判断
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
                "🟢 当前价格进入模型重仓区。"
            )

        elif (
            entry_price is not None
            and valuation_price <= entry_price
        ):

            st.success(
                "🟢 当前价格进入模型建仓区。"
            )

        elif valuation_price <= normal_value:

            st.info(
                "🟡 当前价格低于中性合理价值，但安全边际一般。"
            )

        elif (
            optimistic_value is not None
            and valuation_price <= optimistic_value
        ):

            st.warning(
                "🟠 当前价格高于中性合理价值，建议等待更好的安全边际。"
            )

        else:

            st.error(
                "🔴 当前价格高于乐观估值，估值偏高。"
            )

    else:

        st.warning(
            "⚠️ 当前尚不足以完成完整估值。"
        )


    # =====================================================
    # K. V11综合投资评级
    # =====================================================

    st.divider()

    st.header(
        "🏆 九、ValueStock AI 综合投资评级"
    )


    # -----------------------------------------------------
    # 财务质量 30分
    # -----------------------------------------------------

    financial_component = (
        financial_quality_score * 0.30
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
    # 盈利能力 15分
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
    # 现金流 15分
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
    # 财务安全 10分
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
    # 估值 10分
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

    raw_total = (
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
                raw_total - risk_penalty
            )
        )
    )


    # -----------------------------------------------------
    # 最终评级
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
            "D：谨慎，暂不适合重仓"
        )

    else:

        final_rating = (
            "E：风险较高"
        )


    r1, r2 = st.columns(2)


    r1.metric(
        "ValueStock AI 综合分",
        f"{final_score} / 100"
    )


    r2.metric(
        "投资评级",
        final_rating
    )


    # =====================================================
    # L. 综合评分表
    # =====================================================

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
            round(financial_component, 1),
            growth_component,
            profitability_component,
            cash_component,
            safety_component,
            valuation_component
        ]

    })


    st.subheader(
        "📊 综合评分构成"
    )


    st.dataframe(
        component_table,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # M. 最终投资结论
    # =====================================================

    st.subheader(
        "🏆 十、最终投资结论"
    )


    if final_score >= 85:

        conclusion = (
            "公司当前综合质量优秀，"
            "若当前股价同时处于建仓或重仓区间，"
            "可进入长期重点研究名单。"
        )

    elif final_score >= 75:

        conclusion = (
            "公司综合质量较好，"
            "具备长期跟踪价值；"
            "真正的投资关键在于估值和未来盈利持续性。"
        )

    elif final_score >= 65:

        conclusion = (
            "公司具备一定投资价值，"
            "但仍存在部分验证环节，"
            "建议等待更明确的经营改善或更好的安全边际。"
        )

    elif final_score >= 50:

        conclusion = (
            "公司存在一定投资风险，"
            "当前不适合仅凭短期利润增长进行重仓。"
        )

    else:

        conclusion = (
            "当前质量与风险收益比较弱，"
            "暂不建议作为长期核心资产。"
        )


    if (
        entry_price is not None
        and valuation_price is not None
        and valuation_price <= entry_price
    ):

        conclusion += (
            " 当前股价已经进入模型建仓价格区间。"
        )

    elif (
        normal_value is not None
        and valuation_price is not None
        and valuation_price <= normal_value
    ):

        conclusion += (
            " 当前价格低于模型中性合理价值，但安全边际仍需观察。"
        )

    elif (
        normal_value is not None
        and valuation_price is not None
        and valuation_price > normal_value
    ):

        conclusion += (
            " 当前价格高于中性合理价值，应重点控制估值风险。"
        )


    st.info(
        conclusion
    )


    # =====================================================
    # N. 数据完整度
    # =====================================================

    st.subheader(
        "📌 十一、模型数据完整度"
    )


    available_items = 0

    total_items = 10


    checks = [

        valuation_price is not None,

        roe is not None,

        revenue_growth is not None,

        profit_growth is not None,

        debt_ratio is not None,

        latest_eps is not None,

        latest_bvps is not None,

        latest_revenue is not None,

        latest_profit is not None,

        latest_cashflow is not None

    ]


    for check in checks:

        if check:
            available_items += 1


    completeness = (
        available_items
        / total_items
        * 100
    )


    st.progress(
        completeness / 100
    )


    st.write(
        f"当前核心数据完整度：{completeness:.0f}%"
    )


    # =====================================================
    # O. 数据诊断
    # =====================================================

    st.subheader(
        "🛠️ 十二、数据接口诊断"
    )


    diagnostic = pd.DataFrame({

        "项目": [
            "实时行情",
            "历史行情",
            "财务指标",
            "ROE",
            "营收增长",
            "净利润增长",
            "资产负债率",
            "EPS",
            "每股净资产",
            "利润表",
            "资产负债表",
            "现金流量表"
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
            if roe is not None
            else "❌ 无数据",

            "✅ 成功"
            if revenue_growth is not None
            else "❌ 无数据",

            "✅ 成功"
            if profit_growth is not None
            else "❌ 无数据",

            "✅ 成功"
            if debt_ratio is not None
            else "❌ 无数据",

            "✅ 成功"
            if latest_eps is not None
            else "❌ 无数据",

            "✅ 成功"
            if latest_bvps is not None
            else "❌ 无数据",

            "✅ 成功"
            if profit is not None
            else "❌ 无数据",

            "✅ 成功"
            if balance is not None
            else "❌ 无数据",

            "✅ 成功"
            if cashflow is not None
            else "❌ 无数据"

        ]

    })


    st.dataframe(
        diagnostic,
        use_container_width=True,
        hide_index=True
    )


    st.divider()

    st.caption(
        "V11：实时行情 + 财务指标 + 三张报表 + 5年财务质量 + PE/PB综合估值 + 投资价格区间 + 综合投资评级。"
    )
