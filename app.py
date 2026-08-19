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


# =========================================================
# 0. 页面设置
# =========================================================

st.set_page_config(
    page_title="ValueStock AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ValueStock AI")
st.subheader("A股长期价值投资分析系统 V13")

st.caption(
    "模块化版本：财务 + 风险 + 估值 + 同行业比较"
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
# 6. 财务报表字段
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
# 7. 获取单家公司年度财务数据
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
# 8. 股票代码输入
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
    # 二、目标公司财务
    # =====================================================

    st.header(
        "📊 二、目标公司财务"
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
        "🚨 四、财务风险"
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


    # =====================================================
    # 五、5年财务质量
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


    q1, q2 = st.columns(2)


    q1.metric(
        "财务质量评分",
        f"{financial_quality['score']}/100"
    )


    q2.metric(
        "财务质量评级",
        financial_quality["rating"]
    )


    # =====================================================
    # 六、估值
    # =====================================================

    st.header(
        "💰 六、估值"
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


    e1, e2, e3, e4 = st.columns(4)


    e1.metric(
        "当前PE",
        "暂无"
        if current_pe is None
        else f"{current_pe:.2f}"
    )


    e2.metric(
        "当前PB",
        "暂无"
        if current_pb is None
        else f"{current_pb:.2f}"
    )


    e3.metric(
        "中性合理价",
        "暂无"
        if normal_value is None
        else f"{normal_value:.2f} 元"
    )


    e4.metric(
        "建仓价",
        "暂无"
        if entry_price is None
        else f"{entry_price:.2f} 元"
    )


    # =====================================================
    # 七、同行业比较
    # =====================================================

    st.header(
        "🏭 七、同行业比较"
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


    if len(peer_codes) < 2:

        st.info(
            "请输入至少2只同行股票，"
            "例如：600406,002028,601179"
        )

    else:

        if len(peer_codes) > 5:

            peer_codes = (
                peer_codes[:5]
            )

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
                "❌ 有效同行公司不足，无法比较。"
            )

        else:

            peer_df = (
                pd.DataFrame(
                    peer_rows
                )
            )


            # -----------------------------------------
            # 比较表
            # -----------------------------------------

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


            # -----------------------------------------
            # 同行平均
            # -----------------------------------------

            st.subheader(
                "📊 同行平均水平"
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

                st.dataframe(
                    summary,
                    use_container_width=True,
                    hide_index=True
                )


            # -----------------------------------------
            # 目标公司 vs 同行
            # -----------------------------------------

            st.subheader(
                "🎯 目标公司相对同行"
            )


            comparison = (
                compare_target_with_average(
                    peer_df,
                    stock_code
                )
            )


            if comparison:

                comparison_df = (
                    pd.DataFrame(
                        comparison
                    )
                )


                st.dataframe(
                    comparison_df,
                    use_container_width=True,
                    hide_index=True
                )


            # -----------------------------------------
            # 同行竞争力评分
            # -----------------------------------------

            peer_score_result = (
                calculate_peer_score(
                    peer_df,
                    stock_code
                )
            )


            ps1, ps2 = st.columns(2)


            ps1.metric(
                "同行竞争力评分",
                f"{peer_score_result['score']}/100"
            )


            ps2.metric(
                "同行竞争力评级",
                peer_score_result["rating"]
            )


            if (
                peer_score_result[
                    "score"
                ] >= 85
            ):

                st.success(
                    "🟢 目标公司在输入的同行中竞争力较强。"
                )


            elif (
                peer_score_result[
                    "score"
                ] >= 70
            ):

                st.info(
                    "🟡 目标公司在输入的同行中具备较好竞争力。"
                )


            elif (
                peer_score_result[
                    "score"
                ] >= 55
            ):

                st.warning(
                    "🟠 目标公司在输入的同行中处于中等水平。"
                )


            else:

                st.error(
                    "🔴 目标公司在输入的同行中竞争力偏弱。"
                )


    # =====================================================
    # 八、综合投资评级
    # =====================================================

    st.header(
        "🏆 八、综合投资评级"
    )


    financial_component = (
        financial_quality[
            "score"
        ]
        * 0.30
    )


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


    growth_component = 0


    if (
        annual_revenue_growth is not None
        and annual_profit_growth is not None
    ):

        growth_average = (
            annual_revenue_growth
            + annual_profit_growth
        ) / 2


        if growth_average >= 20:

            growth_component = 20

        elif growth_average >= 15:

            growth_component = 17

        elif growth_average >= 10:

            growth_component = 14

        elif growth_average >= 5:

            growth_component = 10

        elif growth_average >= 0:

            growth_component = 6

        else:

            growth_component = 2


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

        rating = (
            "A：优秀长期价值候选"
        )

    elif final_score >= 75:

        rating = (
            "B：优质，值得长期跟踪"
        )

    elif final_score >= 65:

        rating = (
            "C：一般，等待更多验证"
        )

    elif final_score >= 50:

        rating = (
            "D：谨慎，不适合重仓"
        )

    else:

        rating = (
            "E：风险较高"
        )


    c1, c2 = st.columns(2)


    c1.metric(
        "综合评分",
        f"{final_score}/100"
    )


    c2.metric(
        "投资评级",
        rating
    )


    # =====================================================
    # 九、投资价格总结
    # =====================================================

    st.header(
        "💰 九、投资价格总结"
    )


    price_summary = pd.DataFrame({

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


    price_summary["价格"] = (
        price_summary["价格"]
        .apply(
            lambda x:
            "暂无"
            if x is None
            else f"{x:.2f} 元"
        )
    )


    st.dataframe(
        price_summary,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # 十、最终结论
    # =====================================================

    st.header(
        "🏆 十、最终投资结论"
    )


    if final_score >= 85:

        conclusion = (
            "综合质量优秀，"
            "具备长期重点研究价值。"
        )

    elif final_score >= 75:

        conclusion = (
            "综合质量较好，"
            "值得长期跟踪，等待合理估值。"
        )

    elif final_score >= 65:

        conclusion = (
            "具备一定投资价值，"
            "但还需要更多验证。"
        )

    elif final_score >= 50:

        conclusion = (
            "风险收益比较一般，"
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
    # 十一、系统诊断
    # =====================================================

    st.header(
        "🛠️ 十一、系统诊断"
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

            "当前PE",

            "合理价"
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
            if peer_input
            else "⏳",

            "✅"
            if current_pe is not None
            else "❌",

            "✅"
            if normal_value is not None
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
    "ValueStock AI V13："
    "财务 + 风险 + 估值 + 同行业比较。"
)
