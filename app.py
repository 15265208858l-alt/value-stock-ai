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

from peer_compare import (
    calculate_peer_score,
    build_peer_summary,
    compare_target_with_average
)

from investment_score import (
    calculate_investment_score
)

from historical_valuation import (
    build_historical_pe,
    calculate_historical_statistics,
    get_historical_valuation_level
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
st.subheader("A股长期价值投资分析系统 V15")

st.caption(
    "财务质量 + 财务排雷 + 当前估值 + 同行业比较 + 历史估值"
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
# 6. 报表字段
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
# 7. 同行公司财务数据
# =========================================================

def get_company_financial_data(
    stock_code
):

    indicators = (
        get_financial_indicators(
            stock_code
        )
    )

    if (
        indicators is None
        or indicators.empty
    ):

        return None

    financial_data = (
        process_financial_indicators(
            indicators
        )
    )

    annual = financial_data[
        "annual"
    ]

    return {

        "roe":
            annual.get(
                "roe"
            ),

        "revenue_growth":
            annual.get(
                "revenue_growth"
            ),

        "profit_growth":
            annual.get(
                "profit_growth"
            ),

        "debt":
            annual.get(
                "debt"
            ),

        "eps":
            annual.get(
                "eps"
            ),

        "bvps":
            annual.get(
                "bvps"
            )
    }


# =========================================================
# 8. 输入
# =========================================================

stock_input = st.text_input(
    "请输入目标股票代码",
    placeholder="例如：600089"
)

peer_input = st.text_input(
    "请输入同行股票代码（2～5只，用英文逗号分隔）",
    placeholder="例如：600406,002028,601179"
)

analyze = st.button(
    "🚀 开始价值投资分析",
    type="primary"
)


# =========================================================
# 9. 主分析
# =========================================================

if analyze:

    stock_code = clean_stock_code(
        stock_input
    )

    if not stock_code:

        st.error(
            "❌ 目标股票请输入6位数字代码"
        )

        st.stop()

    st.info(
        f"正在分析 {stock_code}，请稍候……"
    )


    # =====================================================
    # 一、行情
    # =====================================================

    st.header(
        "📌 一、目标公司行情"
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

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "股票名称",
        stock_name
    )

    c2.metric(
        "当前价格",
        "暂无"
        if current_price is None
        else f"{current_price:.2f} 元"
    )

    c3.metric(
        "涨跌幅",
        "暂无"
        if day_change is None
        else f"{day_change:.2f}%"
    )

    c4.metric(
        "动态PE",
        "暂无"
        if realtime_pe is None
        else f"{realtime_pe:.2f}"
    )


    # =====================================================
    # 二、财务
    # =====================================================

    st.header(
        "📊 二、财务分析"
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

    financial_data = (
        process_financial_indicators(
            indicators
        )
    )

    latest = financial_data[
        "latest"
    ]

    annual = financial_data[
        "annual"
    ]

    trend = financial_data[
        "trend"
    ]

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
    # 四、财务风险
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

    st.write(
        f"**风险等级：{risk_level}**"
    )

    st.write(
        f"**风险评分：{risk_score}**"
    )

    if risk_result[
        "risk_items"
    ]:

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
    # 五、财务质量
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

    financial_quality = (
        calculate_financial_quality(
            trend,
            cash_result["ratio"]
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


    # =====================================================
    # 六、当前估值
    # =====================================================

    st.header(
        "💰 六、当前价值估值"
    )

    current_pe = None
    current_pb = None

    if (
        current_price is not None
        and annual_eps is not None
        and annual_eps > 0
    ):

        current_pe = (
            current_price
            / annual_eps
        )

    if (
        current_price is not None
        and annual_bvps is not None
        and annual_bvps > 0
    ):

        current_pb = (
            current_price
            / annual_bvps
        )

    if annual_roe is not None:

        if annual_roe >= 20:

            pe_c = 14.0
            pe_n = 18.0
            pe_o = 22.0

        elif annual_roe >= 15:

            pe_c = 13.0
            pe_n = 17.0
            pe_o = 21.0

        elif annual_roe >= 10:

            pe_c = 10.0
            pe_n = 14.0
            pe_o = 18.0

        else:

            pe_c = 8.0
            pe_n = 11.0
            pe_o = 14.0

    else:

        pe_c = 10.0
        pe_n = 14.0
        pe_o = 18.0

    pb_c = 1.5
    pb_n = 2.0
    pb_o = 2.5

    if annual_roe is not None:

        if annual_roe >= 20:

            pe_weight = 0.75
            pb_weight = 0.25

        elif annual_roe >= 15:

            pe_weight = 0.70
            pb_weight = 0.30

        elif annual_roe >= 10:

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

            eps=annual_eps,

            bvps=annual_bvps,

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

    normal_value = (
        valuation_result[
            "normal"
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

    optimistic_value = (
        valuation_result[
            "optimistic"
        ]
    )

    v1, v2, v3, v4 = st.columns(4)

    v1.metric(
        "当前PE",
        "暂无"
        if current_pe is None
        else f"{current_pe:.2f}"
    )

    v2.metric(
        "当前PB",
        "暂无"
        if current_pb is None
        else f"{current_pb:.2f}"
    )

    v3.metric(
        "中性合理价",
        "暂无"
        if normal_value is None
        else f"{normal_value:.2f} 元"
    )

    v4.metric(
        "建仓价",
        "暂无"
        if entry_price is None
        else f"{entry_price:.2f} 元"
    )


    # =====================================================
    # 七、历史估值 V15
    # =====================================================

    st.header(
        "📊 七、历史PE估值"
    )

    historical_pe = (
        build_historical_pe(
            history,
            trend,
            max_years=10
        )
    )

    historical_stats = (
        calculate_historical_statistics(
            historical_pe,
            current_pe
        )
    )

    if (
        historical_pe is not None
        and not historical_pe.empty
    ):

        display_history_pe = (
            historical_pe.copy()
        )

        display_history_pe[
            "年末收盘价"
        ] = (
            display_history_pe[
                "年末收盘价"
            ]
            .round(2)
        )

        display_history_pe[
            "EPS"
        ] = (
            display_history_pe[
                "EPS"
            ]
            .round(2)
        )

        display_history_pe[
            "PE"
        ] = (
            display_history_pe[
                "PE"
            ]
            .round(2)
        )

        st.subheader(
            "📅 历史PE序列"
        )

        st.dataframe(
            display_history_pe,
            use_container_width=True,
            hide_index=True
        )


        h1, h2, h3 = st.columns(3)

        h1.metric(
            "历史最低PE",
            "暂无"
            if historical_stats["min"] is None
            else f"{historical_stats['min']:.2f}"
        )

        h2.metric(
            "历史中位PE",
            "暂无"
            if historical_stats["median"] is None
            else f"{historical_stats['median']:.2f}"
        )

        h3.metric(
            "历史最高PE",
            "暂无"
            if historical_stats["max"] is None
            else f"{historical_stats['max']:.2f}"
        )


        h4, h5, h6 = st.columns(3)

        h4.metric(
            "历史25%分位",
            "暂无"
            if historical_stats["q25"] is None
            else f"{historical_stats['q25']:.2f}"
        )

        h5.metric(
            "历史75%分位",
            "暂无"
            if historical_stats["q75"] is None
            else f"{historical_stats['q75']:.2f}"
        )

        h6.metric(
            "当前PE历史分位",
            "暂无"
            if historical_stats["percentile"] is None
            else f"{historical_stats['percentile']:.1f}%"
        )


        if historical_stats["deviation"] is not None:

            st.metric(
                "当前PE相对历史中位PE偏离",
                f"{historical_stats['deviation']:.2f}%"
            )


        historical_level = (
            get_historical_valuation_level(
                historical_stats[
                    "percentile"
                ]
            )
        )

        st.write(
            f"**历史估值区域：{historical_level}**"
        )


        if historical_level == "历史低位":

            st.success(
                "🟢 当前估值处于历史偏低区域。"
            )

        elif historical_level == "历史中低位":

            st.success(
                "🟢 当前估值处于历史中低区域。"
            )

        elif historical_level == "历史中枢":

            st.info(
                "🟡 当前估值接近历史估值中枢。"
            )

        elif historical_level == "历史中高位":

            st.warning(
                "🟠 当前估值处于历史中高区域。"
            )

        elif historical_level == "历史高位":

            st.error(
                "🔴 当前估值处于历史高位区域。"
            )

    else:

        historical_level = "数据不足"

        st.warning(
            "⚠️ 当前财务和历史价格数据不足，"
            "暂时无法形成有效的历史PE序列。"
        )


    # =====================================================
    # 八、同行业比较
    # =====================================================

    st.header(
        "🏭 八、同行业比较"
    )

    peer_codes = []

    if peer_input:

        for code in peer_input.split(","):

            clean_code = (
                clean_stock_code(
                    code
                )
            )

            if (
                clean_code
                and clean_code != stock_code
                and clean_code not in peer_codes
            ):

                peer_codes.append(
                    clean_code
                )

    peer_score = None

    peer_rating = "数据不足"

    if len(peer_codes) < 2:

        st.info(
            "请输入至少2只同行股票，"
            "例如：600406,002028,601179"
        )

    else:

        if len(peer_codes) > 5:

            peer_codes = peer_codes[:5]

            st.warning(
                "最多比较5只同行股票。"
            )

        compare_codes = [
            stock_code
        ] + peer_codes

        peer_rows = []

        progress = st.progress(0)

        for index, code in enumerate(
            compare_codes
        ):

            try:

                data = (
                    get_company_financial_data(
                        code
                    )
                )

                if data is None:

                    progress.progress(
                        (index + 1)
                        / len(compare_codes)
                    )

                    continue

                peer_realtime = (
                    get_realtime_market(
                        code
                    )
                )

                name = code
                price = None

                if peer_realtime:

                    name = peer_realtime.get(
                        "名称",
                        code
                    )

                    price = safe_float(
                        peer_realtime.get(
                            "最新价"
                        )
                    )

                if price is None:

                    peer_history = (
                        get_history_data(
                            code
                        )
                    )

                    price = (
                        get_latest_price(
                            peer_history
                        )
                    )

                eps = data.get(
                    "eps"
                )

                bvps = data.get(
                    "bvps"
                )

                pe = None
                pb = None

                if (
                    price is not None
                    and eps is not None
                    and eps > 0
                ):

                    pe = (
                        price
                        / eps
                    )

                if (
                    price is not None
                    and bvps is not None
                    and bvps > 0
                ):

                    pb = (
                        price
                        / bvps
                    )

                peer_rows.append({

                    "代码": code,

                    "名称": name,

                    "价格": price,

                    "ROE": data.get(
                        "roe"
                    ),

                    "营收增长率":
                        data.get(
                            "revenue_growth"
                        ),

                    "净利润增长率":
                        data.get(
                            "profit_growth"
                        ),

                    "资产负债率":
                        data.get(
                            "debt"
                        ),

                    "PE": pe,

                    "PB": pb,

                    "EPS": eps,

                    "BPS": bvps
                })

            except Exception:

                pass

            progress.progress(
                (index + 1)
                / len(compare_codes)
            )


        if len(peer_rows) < 2:

            st.error(
                "❌ 有效同行公司不足。"
            )

        else:

            peer_df = pd.DataFrame(
                peer_rows
            )

            st.subheader(
                "📊 同行业核心指标"
            )

            display_df = peer_df.copy()

            for col in [
                "价格",
                "ROE",
                "营收增长率",
                "净利润增长率",
                "资产负债率",
                "PE",
                "PB",
                "EPS",
                "BPS"
            ]:

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

            summary = (
                build_peer_summary(
                    peer_df
                )
            )

            if (
                summary is not None
                and not summary.empty
            ):

                st.subheader(
                    "📊 同行平均"
                )

                st.dataframe(
                    summary,
                    use_container_width=True,
                    hide_index=True
                )

            comparison = (
                compare_target_with_average(
                    peer_df,
                    stock_code
                )
            )

            if comparison:

                st.subheader(
                    "🎯 目标公司相对同行"
                )

                st.dataframe(
                    pd.DataFrame(
                        comparison
                    ),
                    use_container_width=True,
                    hide_index=True
                )

            peer_score_result = (
                calculate_peer_score(
                    peer_df,
                    stock_code
                )
            )

            peer_score = (
                peer_score_result[
                    "score"
                ]
            )

            peer_rating = (
                peer_score_result[
                    "rating"
                ]
            )

            p1, p2 = st.columns(2)

            p1.metric(
                "同行竞争力",
                f"{peer_score}/100"
            )

            p2.metric(
                "同行评级",
                peer_rating
            )


    # =====================================================
    # 九、综合投资价值评分
    # =====================================================

    st.header(
        "🏆 九、综合投资价值评分"
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


    investment_result = (
        calculate_investment_score(

            financial_score=(
                financial_quality[
                    "score"
                ]
            ),

            peer_score=peer_score,

            valuation_gap=valuation_gap,

            risk_score=risk_score
        )
    )


    investment_score = (
        investment_result[
            "score"
        ]
    )

    investment_rating = (
        investment_result[
            "rating"
        ]
    )


    s1, s2 = st.columns(2)


    s1.metric(
        "投资价值评分",
        f"{investment_score}/100"
    )


    s2.metric(
        "投资评级",
        investment_rating
    )


    # =====================================================
    # 十、投资价格
    # =====================================================

    st.header(
        "💰 十、投资价格区间"
    )


    price_table = pd.DataFrame({

        "价格类型": [

            "当前价格",

            "重仓参考价",

            "建仓参考价",

            "中性合理价",

            "乐观估值"
        ],

        "价格": [

            current_price,

            heavy_price,

            entry_price,

            normal_value,

            optimistic_value
        ]
    })


    price_table["价格"] = (
        price_table["价格"]
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
    # 十一、最终投资结论
    # =====================================================

    st.header(
        "🏆 十一、最终投资结论"
    )


    if investment_score >= 85:

        conclusion = (
            "🟢 优质公司 + 估值具有较好吸引力，"
            "值得进入长期重点研究名单。"
        )

    elif investment_score >= 75:

        conclusion = (
            "🟢 公司质量较好，"
            "当前估值总体合理，值得长期跟踪。"
        )

    elif investment_score >= 65:

        conclusion = (
            "🟡 公司具备一定价值，"
            "但建议等待更好的安全边际。"
        )

    elif investment_score >= 50:

        conclusion = (
            "🟠 当前投资吸引力一般，"
            "不宜仅凭单项指标做决定。"
        )

    else:

        conclusion = (
            "🔴 当前风险收益比较弱，"
            "暂不适合作为长期核心资产。"
        )


    st.info(
        conclusion
    )


    if risk_result[
        "risk_items"
    ]:

        st.subheader(
            "⚠️ 核心风险"
        )

        for item in (
            risk_result[
                "risk_items"
            ]
        ):

            st.write(
                f"- {item}"
            )


    # =====================================================
    # 十二、系统诊断
    # =====================================================

    st.header(
        "🛠️ 十二、系统诊断"
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

            "peer_compare.py",

            "investment_score.py",

            "historical_valuation.py"
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
            if peer_score is not None
            else "⏳",

            "✅",

            "✅"
        ]
    })


    st.dataframe(
        diagnostic,
        use_container_width=True,
        hide_index=True
    )


st.divider()


st.caption(
    "ValueStock AI V15："
    "财务质量 + 财务风险 + 当前估值 + "
    "历史估值 + 同行业竞争力 + 综合投资价值。"
)
