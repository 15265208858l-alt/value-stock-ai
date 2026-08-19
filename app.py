import streamlit as st
import akshare as ak
import pandas as pd

from financial import (
    process_financial_indicators,
    calculate_financial_quality
)

from risk import (
    analyze_financial_risk
)

from valuation import (
    calculate_valuation_scenarios
)


# =========================================================
# 0. 页面设置
# =========================================================

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("A股长期价值投资分析系统 V12.5")

st.caption(
    "模块化版本："
    "financial.py + risk.py + valuation.py"
)

st.divider()


# =========================================================
# 1. 基础函数
# =========================================================

def safe_float(value):

    try:

        if value is None:
            return None

        text = str(value).strip()

        if text in [
            "",
            "--",
            "None",
            "none",
            "NaN",
            "nan"
        ]:
            return None

        text = text.replace(",", "")
        text = text.replace("%", "")

        return float(text)

    except Exception:

        return None


def clean_stock_code(code):

    if code is None:
        return ""

    code = str(code).strip()

    if len(code) != 6:
        return ""

    if not code.isdigit():
        return ""

    return code


def get_market_code(stock_code):

    if stock_code.startswith(("6", "68")):
        return "sh" + stock_code

    if stock_code.startswith(("0", "3")):
        return "sz" + stock_code

    if stock_code.startswith(("4", "8")):
        return "bj" + stock_code

    return stock_code


def find_column(df, candidates):

    if df is None or df.empty:
        return None

    for col in candidates:

        if col in df.columns:
            return col

    return None


def format_money(value):

    if value is None:
        return "暂无"

    try:

        return f"{value / 1e8:.2f} 亿元"

    except Exception:

        return "暂无"


# =========================================================
# 2. 实时行情
# =========================================================

@st.cache_data(ttl=60)
def get_realtime_market(stock_code):

    try:

        data = ak.stock_zh_a_spot_em()

        if data is None or data.empty:
            return None

        code_col = find_column(
            data,
            [
                "代码",
                "股票代码"
            ]
        )

        if code_col is None:
            return None

        result = data[
            data[code_col].astype(str)
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

    try:

        data = ak.stock_zh_a_hist_tx(
            symbol=get_market_code(
                stock_code
            ),
            start_date="20200101",
            end_date="20500101",
            adjust=""
        )

        if data is not None and not data.empty:
            return data

    except Exception:
        pass

    return None


def get_latest_price(history):

    if history is None or history.empty:
        return None

    if "收盘" in history.columns:

        return safe_float(
            history.iloc[-1]["收盘"]
        )

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

    try:

        data = (
            ak.stock_financial_analysis_indicator(
                symbol=stock_code
            )
        )

        if data is not None and not data.empty:

            return data

    except Exception:
        pass


    try:

        data = (
            ak.stock_financial_analysis_indicator_em(
                symbol=stock_code,
                indicator="按报告期"
            )
        )

        if data is not None and not data.empty:

            return data

    except Exception:
        pass


    return None


# =========================================================
# 5. 三大报表
# =========================================================

@st.cache_data(ttl=3600)
def get_financial_report(
    stock_code,
    report_type
):

    try:

        data = ak.stock_financial_report_sina(
            stock=get_market_code(
                stock_code
            ),
            symbol=report_type
        )

        if data is not None and not data.empty:

            return data

    except Exception:
        pass

    return None


# =========================================================
# 6. 报表关键字段
# =========================================================

def get_latest_report_value(
    df,
    candidates
):

    if df is None or df.empty:
        return None

    col = find_column(
        df,
        candidates
    )

    if col is None:
        return None

    return safe_float(
        df.iloc[0][col]
    )


def get_report_metrics(
    profit,
    balance,
    cashflow
):

    return {

        "revenue":
            get_latest_report_value(
                profit,
                [
                    "营业总收入",
                    "营业收入",
                    "一、营业总收入"
                ]
            ),

        "net_profit":
            get_latest_report_value(
                profit,
                [
                    "归属于母公司所有者的净利润",
                    "归属于母公司股东的净利润",
                    "净利润",
                    "五、净利润"
                ]
            ),

        "receivable":
            get_latest_report_value(
                balance,
                [
                    "应收账款",
                    "应收款项"
                ]
            ),

        "inventory":
            get_latest_report_value(
                balance,
                [
                    "存货"
                ]
            ),

        "operating_cashflow":
            get_latest_report_value(
                cashflow,
                [
                    "经营活动产生的现金流量净额",
                    "经营活动现金流量净额"
                ]
            )
    }


# =========================================================
# 7. 股票输入
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
# 8. 主分析
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
    # 一、行情
    # =====================================================

    st.header(
        "📌 一、行情"
    )


    realtime = (
        get_realtime_market(
            stock_code
        )
    )


    history = (
        get_history_data(
            stock_code
        )
    )


    stock_name = stock_code

    current_price = None

    day_change = None

    realtime_pe = None


    if realtime:

        stock_name = realtime.get(
            "名称",
            stock_code
        )

        current_price = (
            safe_float(
                realtime.get(
                    "最新价"
                )
            )
        )

        day_change = (
            safe_float(
                realtime.get(
                    "涨跌幅"
                )
            )
        )

        realtime_pe = (
            safe_float(
                realtime.get(
                    "市盈率-动态"
                )
            )
        )


    if current_price is None:

        current_price = (
            get_latest_price(
                history
            )
        )


    a1, a2, a3, a4 = st.columns(4)


    a1.metric(
        "股票名称",
        stock_name
    )


    a2.metric(
        "当前价格",
        "暂无"
        if current_price is None
        else f"{current_price:.2f} 元"
    )


    a3.metric(
        "涨跌幅",
        "暂无"
        if day_change is None
        else f"{day_change:.2f}%"
    )


    a4.metric(
        "动态PE",
        "暂无"
        if realtime_pe is None
        else f"{realtime_pe:.2f}"
    )


    if history is not None:

        st.success(
            "✅ 历史行情获取成功"
        )

    else:

        st.warning(
            "⚠️ 历史行情暂时无法获取"
        )


    # =====================================================
    # 二、财务指标
    # =====================================================

    st.header(
        "📊 二、财务指标"
    )


    indicators = (
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
        "✅ 财务指标获取成功"
    )


    financial_data = (
        process_financial_indicators(
            indicators
        )
    )


    latest = (
        financial_data[
            "latest"
        ]
    )


    annual = (
        financial_data[
            "annual"
        ]
    )


    trend = (
        financial_data[
            "trend"
        ]
    )


    latest_roe = latest.get(
        "roe"
    )

    latest_revenue_growth = (
        latest.get(
            "revenue_growth"
        )
    )

    latest_profit_growth = (
        latest.get(
            "profit_growth"
        )
    )

    latest_debt = latest.get(
        "debt"
    )


    annual_roe = annual.get(
        "roe"
    )

    annual_revenue_growth = (
        annual.get(
            "revenue_growth"
        )
    )

    annual_profit_growth = (
        annual.get(
            "profit_growth"
        )
    )

    annual_debt = annual.get(
        "debt"
    )

    annual_eps = annual.get(
        "eps"
    )

    annual_bvps = annual.get(
        "bvps"
    )


    c1, c2, c3, c4 = st.columns(4)


    c1.metric(
        "最新ROE",
        "暂无"
        if latest_roe is None
        else f"{latest_roe:.2f}%"
    )


    c2.metric(
        "营收增长",
        "暂无"
        if latest_revenue_growth is None
        else f"{latest_revenue_growth:.2f}%"
    )


    c3.metric(
        "净利润增长",
        "暂无"
        if latest_profit_growth is None
        else f"{latest_profit_growth:.2f}%"
    )


    c4.metric(
        "资产负债率",
        "暂无"
        if latest_debt is None
        else f"{latest_debt:.2f}%"
    )


    st.subheader(
        "最近完整年度"
    )


    y1, y2, y3, y4 = st.columns(4)


    y1.metric(
        "年度ROE",
        "暂无"
        if annual_roe is None
        else f"{annual_roe:.2f}%"
    )


    y2.metric(
        "年度EPS",
        "暂无"
        if annual_eps is None
        else f"{annual_eps:.2f} 元"
    )


    y3.metric(
        "年度BPS",
        "暂无"
        if annual_bvps is None
        else f"{annual_bvps:.2f} 元"
    )


    y4.metric(
        "年度负债率",
        "暂无"
        if annual_debt is None
        else f"{annual_debt:.2f}%"
    )


    # =====================================================
    # 三、三大报表
    # =====================================================

    st.header(
        "💰 三、三大报表"
    )


    profit = (
        get_financial_report(
            stock_code,
            "利润表"
        )
    )


    balance = (
        get_financial_report(
            stock_code,
            "资产负债表"
        )
    )


    cashflow = (
        get_financial_report(
            stock_code,
            "现金流量表"
        )
    )


    metrics = (
        get_report_metrics(
            profit,
            balance,
            cashflow
        )
    )


    latest_revenue = metrics[
        "revenue"
    ]


    latest_profit = metrics[
        "net_profit"
    ]


    latest_receivable = metrics[
        "receivable"
    ]


    latest_inventory = metrics[
        "inventory"
    ]


    latest_cashflow = metrics[
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
        f"三大报表：{report_count}/3"
    )


    d1, d2, d3, d4, d5 = st.columns(5)


    d1.metric(
        "营业收入",
        format_money(
            latest_revenue
        )
    )


    d2.metric(
        "净利润",
        format_money(
            latest_profit
        )
    )


    d3.metric(
        "经营现金流",
        format_money(
            latest_cashflow
        )
    )


    d4.metric(
        "应收账款",
        format_money(
            latest_receivable
        )
    )


    d5.metric(
        "存货",
        format_money(
            latest_inventory
        )
    )


    # =====================================================
    # 四、财务排雷模块
    # =====================================================

    st.header(
        "🚨 四、财务排雷"
    )


    risk_result = (
        analyze_financial_risk(

            operating_cashflow=(
                latest_cashflow
            ),

            net_profit=(
                latest_profit
            ),

            receivable=(
                latest_receivable
            ),

            revenue=(
                latest_revenue
            ),

            inventory=(
                latest_inventory
            ),

            roe=(
                annual_roe
            ),

            debt_ratio=(
                annual_debt
            )
        )
    )


    risk_score = (
        risk_result[
            "score"
        ]
    )


    risk_level = (
        risk_result[
            "level"
        ]
    )


    cash_result = (
        risk_result[
            "cashflow"
        ]
    )


    receivable_result = (
        risk_result[
            "receivable"
        ]
    )


    inventory_result = (
        risk_result[
            "inventory"
        ]
    )


    roe_result = (
        risk_result[
            "roe"
        ]
    )


    debt_result = (
        risk_result[
            "debt"
        ]
    )


    r1, r2, r3 = st.columns(3)


    r1.metric(
        "现金流/净利润",
        "暂无"
        if cash_result[
            "ratio"
        ] is None
        else f"{cash_result['ratio']:.2f}"
    )


    r2.metric(
        "应收账款/营收",
        "暂无"
        if receivable_result[
            "ratio"
        ] is None
        else f"{receivable_result['ratio']:.2%}"
    )


    r3.metric(
        "存货/营收",
        "暂无"
        if inventory_result[
            "ratio"
        ] is None
        else f"{inventory_result['ratio']:.2%}"
    )


    st.subheader(
        "风险判断"
    )


    st.write(
        f"**综合风险等级：{risk_level}**"
    )


    st.write(
        f"**风险评分：{risk_score}**"
    )


    st.write(
        f"现金流：{cash_result['level']} —— "
        f"{cash_result['message']}"
    )


    st.write(
        f"应收账款：{receivable_result['level']} —— "
        f"{receivable_result['message']}"
    )


    st.write(
        f"存货：{inventory_result['level']} —— "
        f"{inventory_result['message']}"
    )


    st.write(
        f"ROE：{roe_result['level']} —— "
        f"{roe_result['message']}"
    )


    st.write(
        f"负债率：{debt_result['level']} —— "
        f"{debt_result['message']}"
    )


    if risk_result[
        "risk_items"
    ]:

        st.warning(
            "⚠️ 存在以下风险信号："
        )

        for item in (
            risk_result[
                "risk_items"
            ]
        ):

            st.write(
                f"- {item}"
            )

    else:

        st.success(
            "🟢 暂未发现明显财务风险信号"
        )


    # =====================================================
    # 五、5年财务质量模块
    # =====================================================

    st.header(
        "⭐ 五、5年财务质量"
    )


    if (
        trend is not None
        and not trend.empty
    ):

        st.dataframe(
            trend,
            use_container_width=True,
            hide_index=True
        )


    cash_profit_ratio = (
        cash_result["ratio"]
    )


    financial_quality = (
        calculate_financial_quality(
            trend,
            cash_profit_ratio
        )
    )


    fq1, fq2 = st.columns(2)


    fq1.metric(
        "财务质量评分",
        f"{financial_quality['score']}/100"
    )


    fq2.metric(
        "财务质量评级",
        financial_quality["rating"]
    )


    quality_table = pd.DataFrame({

        "维度": [
            "ROE及盈利能力",
            "营收成长",
            "净利润成长",
            "财务安全",
            "现金流质量"
        ],

        "得分": [

            f"{financial_quality['roe_score']}/20",

            f"{financial_quality['growth_score']}/20",

            f"{financial_quality['profit_score']}/20",

            f"{financial_quality['debt_score']}/20",

            f"{financial_quality['cash_score']}/20"
        ]
    })


    st.dataframe(
        quality_table,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # 六、估值模块
    # =====================================================

    st.header(
        "💰 六、长期价值估值"
    )


    valuation_eps = annual_eps

    valuation_bvps = annual_bvps

    valuation_roe = annual_roe


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


    e1, e2, e3, e4 = st.columns(4)


    e1.metric(
        "当前价格",
        "暂无"
        if current_price is None
        else f"{current_price:.2f} 元"
    )


    e2.metric(
        "年度EPS",
        "暂无"
        if valuation_eps is None
        else f"{valuation_eps:.2f} 元"
    )


    e3.metric(
        "当前PE",
        "暂无"
        if current_pe is None
        else f"{current_pe:.2f} 倍"
    )


    e4.metric(
        "当前PB",
        "暂无"
        if current_pb is None
        else f"{current_pb:.2f} 倍"
    )


    # =====================================================
    # 七、估值参数
    # =====================================================

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


    pe_c = st.number_input(
        "保守PE",
        3.0,
        50.0,
        pe_conservative,
        1.0
    )


    pe_n = st.number_input(
        "中性PE",
        3.0,
        50.0,
        pe_normal,
        1.0
    )


    pe_o = st.number_input(
        "乐观PE",
        3.0,
        50.0,
        pe_optimistic,
        1.0
    )


    pb_c = st.number_input(
        "保守PB",
        0.3,
        10.0,
        1.5,
        0.1
    )


    pb_n = st.number_input(
        "中性PB",
        0.3,
        10.0,
        2.0,
        0.1
    )


    pb_o = st.number_input(
        "乐观PB",
        0.3,
        10.0,
        2.5,
        0.1
    )


    # =====================================================
    # 八、PE/PB权重
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


    valuation_result = (
        calculate_valuation_scenarios(

            eps=valuation_eps,

            bvps=valuation_bvps,

            conservative_pe=pe_c,

            normal_pe=pe_n,

            optimistic_pe=pe_o,

            conservative_pb=pb_c,

            normal_pb=pb_n,

            optimistic_pb=pb_o,

            pe_weight=pe_weight,

            pb_weight=pb_weight
        )
    )


    conservative_value = (
        valuation_result[
            "conservative"
        ]
    )


    normal_value = (
        valuation_result[
            "normal"
        ]
    )


    optimistic_value = (
        valuation_result[
            "optimistic"
        ]
    )


    entry_price = (
        valuation_result[
            "entry_price"
        ]
    )


    heavy_price = (
        valuation_result[
            "heavy_price"
        ]
    )


    # =====================================================
    # 九、估值结果
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


    valuation_table[
        "综合估值"
    ] = (
        valuation_table[
            "综合估值"
        ]
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
    # 十、投资价格区间
    # =====================================================

    st.subheader(
        "💰 投资价格区间"
    )


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
    # 十一、价格判断
    # =====================================================

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


    # =====================================================
    # 十二、综合评分
    # =====================================================

    st.header(
        "🏆 十二、ValueStock AI综合投资评级"
    )


    financial_component = (
        financial_quality[
            "score"
        ]
        * 0.30
    )


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


    cash_component = 0


    if (
        cash_result["ratio"]
        is not None
    ):

        ratio = (
            cash_result["ratio"]
        )


        if ratio >= 1:

            cash_component = 15

        elif ratio >= 0.8:

            cash_component = 13

        elif ratio >= 0.6:

            cash_component = 10

        elif ratio >= 0.3:

            cash_component = 6

        elif ratio >= 0:

            cash_component = 3


    safety_component = 0


    if annual_debt is not None:

        if annual_debt < 40:

            safety_component = 10

        elif annual_debt < 50:

            safety_component = 9

        elif annual_debt < 60:

            safety_component = 7

        elif annual_debt < 70:

            safety_component = 5

        else:

            safety_component = 2


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


    if risk_score >= 10:

        risk_penalty = 12

    elif risk_score >= 7:

        risk_penalty = 8

    elif risk_score >= 4:

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


    s1, s2 = st.columns(2)


    s1.metric(
        "综合评分",
        f"{final_score}/100"
    )


    s2.metric(
        "投资评级",
        final_rating
    )


    # =====================================================
    # 十三、最终结论
    # =====================================================

    st.header(
        "🏆 十三、最终投资结论"
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


    # =====================================================
    # 十四、数据诊断
    # =====================================================

    st.header(
        "🛠️ 十四、系统诊断"
    )


    diagnostic = pd.DataFrame({

        "模块": [

            "历史行情",

            "财务指标",

            "利润表",

            "资产负债表",

            "现金流量表",

            "financial.py",

            "risk.py",

            "valuation.py",

            "当前PE",

            "合理价",

            "建仓价",

            "重仓价"

        ],

        "状态": [

            "✅"
            if history is not None
            else "❌",

            "✅"
            if indicators is not None
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

            "✅",

            "✅",

            "✅",

            "✅"
            if current_pe is not None
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


st.divider()


st.caption(
    "ValueStock AI V12.5："
    "财务、风险、估值三大模块正式分离。"
)
