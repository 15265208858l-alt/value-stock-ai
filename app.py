import streamlit as st
import pandas as pd

from data import (
    clean_stock_code,
    load_stock_data,
    check_data_completeness,
    get_latest_price
)

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

from adaptive_valuation import (
    detect_valuation_model,
    get_valuation_config
)

from historical_valuation import (
    build_historical_pe,
    calculate_historical_statistics,
    get_historical_valuation_level
)

from peer_compare import (
    calculate_peer_score,
    build_peer_summary,
    compare_target_with_average
)

from investment_score import (
    calculate_investment_score
)

from investment_decision import (
    make_investment_decision
)

from industry import (
    get_peer_candidates
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

st.subheader(
    "A股长期价值投资分析系统 V16.5"
)

st.caption(
    "统一数据中心 + 财务质量 + 财务排雷 + "
    "行业自适应估值 + 历史估值 + 同行业比较 + 综合投资评分"
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


def find_column(df, candidates):

    if df is None or df.empty:
        return None

    for column in candidates:
        if column in df.columns:
            return column

    return None


def format_money(value):

    if value is None:
        return "暂无"

    try:
        return f"{value / 1e8:.2f} 亿元"
    except Exception:
        return "暂无"


def get_latest_report_value(df, candidates):

    if df is None or df.empty:
        return None

    column = find_column(df, candidates)

    if column is None:
        return None

    return safe_float(df.iloc[0][column])


def get_report_metrics(profit, balance, cashflow):

    return {
        "revenue": get_latest_report_value(
            profit,
            ["营业总收入", "营业收入", "一、营业总收入"]
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
            ["应收账款", "应收款项"]
        ),
        "inventory": get_latest_report_value(
            balance,
            ["存货"]
        ),
        "operating_cashflow": get_latest_report_value(
            cashflow,
            [
                "经营活动产生的现金流量净额",
                "经营活动现金流量净额"
            ]
        )
    }


def get_company_annual_data(stock_code):

    stock_data = load_stock_data(stock_code)

    if stock_data is None:
        return None

    indicators = stock_data["indicators"]

    if indicators is None or indicators.empty:
        return None

    financial_data = process_financial_indicators(indicators)
    annual = financial_data["annual"]

    return {
        "roe": annual.get("roe"),
        "revenue_growth": annual.get("revenue_growth"),
        "profit_growth": annual.get("profit_growth"),
        "debt": annual.get("debt"),
        "eps": annual.get("eps"),
        "bvps": annual.get("bvps")
    }


# =========================================================
# 2. 输入区
# =========================================================

stock_input = st.text_input(
    "请输入目标股票代码",
    placeholder="例如：600089"
)

peer_input = st.text_input(
    "同行股票代码（自动识别失败时手动输入，2～5只）",
    placeholder="例如：600406,002028,601179"
)

analyze = st.button(
    "🚀 开始价值投资分析",
    type="primary"
)


# =========================================================
# 3. 主分析
# =========================================================

if analyze:

    stock_code = clean_stock_code(stock_input)

    if not stock_code:
        st.error("❌ 请输入6位数字股票代码")
        st.stop()

    # =====================================================
    # 一、统一加载数据
    # =====================================================

    st.header("📡 一、数据中心")

    with st.spinner("正在从数据中心加载A股数据……"):
        stock_data = load_stock_data(stock_code)

    if stock_data is None:
        st.error("❌ 股票代码无效或数据加载失败")
        st.stop()

    completeness = check_data_completeness(stock_data)

    dc1, dc2, dc3 = st.columns(3)

    dc1.metric("数据完整度", f"{completeness['score']}%")
    dc2.metric("已获取模块", f"{completeness['available']}/{completeness['total']}")
    dc3.metric("数据质量", completeness["level"])

    # =====================================================
    # 二、行情
    # =====================================================

    st.header("📌 二、目标公司行情")

    market = stock_data["market"]
    history = stock_data["history"]

    stock_name = stock_code
    current_price = None
    day_change = None
    realtime_pe = None

    if market:
        stock_name = market.get("名称", stock_code)
        current_price = safe_float(market.get("最新价"))
        day_change = safe_float(market.get("涨跌幅"))
        realtime_pe = safe_float(market.get("市盈率-动态"))

    if current_price is None:
        current_price = get_latest_price(history)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("股票名称", stock_name)
    c2.metric("当前价格", "暂无" if current_price is None else f"{current_price:.2f} 元")
    c3.metric("涨跌幅", "暂无" if day_change is None else f"{day_change:.2f}%")
    c4.metric("动态PE", "暂无" if realtime_pe is None else f"{realtime_pe:.2f}")

    if history is not None:
        st.success("✅ 历史行情获取成功")
    else:
        st.warning("⚠️ 历史行情暂时无法获取")

    # =====================================================
    # 三、财务分析
    # =====================================================

    st.header("📊 三、财务分析")

    indicators = stock_data["indicators"]

    if indicators is None or indicators.empty:
        st.error("❌ 财务指标获取失败")
        st.stop()

    financial_data = process_financial_indicators(indicators)
    latest = financial_data["latest"]
    annual = financial_data["annual"]
    trend = financial_data["trend"]

    latest_roe = latest.get("roe")
    latest_revenue_growth = latest.get("revenue_growth")
    latest_profit_growth = latest.get("profit_growth")
    latest_debt = latest.get("debt")

    annual_roe = annual.get("roe")
    annual_revenue_growth = annual.get("revenue_growth")
    annual_profit_growth = annual.get("profit_growth")
    annual_debt = annual.get("debt")
    annual_eps = annual.get("eps")
    annual_bvps = annual.get("bvps")

    f1, f2, f3, f4 = st.columns(4)

    f1.metric("最新ROE", "暂无" if latest_roe is None else f"{latest_roe:.2f}%")
    f2.metric("营收增长", "暂无" if latest_revenue_growth is None else f"{latest_revenue_growth:.2f}%")
    f3.metric("净利润增长", "暂无" if latest_profit_growth is None else f"{latest_profit_growth:.2f}%")
    f4.metric("资产负债率", "暂无" if latest_debt is None else f"{latest_debt:.2f}%")

    st.subheader("最近完整年度")

    y1, y2, y3, y4 = st.columns(4)

    y1.metric("年度ROE", "暂无" if annual_roe is None else f"{annual_roe:.2f}%")
    y2.metric("年度EPS", "暂无" if annual_eps is None else f"{annual_eps:.2f} 元")
    y3.metric("年度BPS", "暂无" if annual_bvps is None else f"{annual_bvps:.2f} 元")
    y4.metric("年度负债率", "暂无" if annual_debt is None else f"{annual_debt:.2f}%")

    # =====================================================
    # 四、三大报表
    # =====================================================

    st.header("💰 四、三大报表")

    profit = stock_data["profit"]
    balance = stock_data["balance"]
    cashflow = stock_data["cashflow"]

    report_metrics = get_report_metrics(profit, balance, cashflow)

    latest_revenue = report_metrics["revenue"]
    latest_profit = report_metrics["net_profit"]
    latest_receivable = report_metrics["receivable"]
    latest_inventory = report_metrics["inventory"]
    latest_cashflow = report_metrics["operating_cashflow"]

    r1, r2, r3, r4, r5 = st.columns(5)

    r1.metric("营业收入", format_money(latest_revenue))
    r2.metric("净利润", format_money(latest_profit))
    r3.metric("经营现金流", format_money(latest_cashflow))
    r4.metric("应收账款", format_money(latest_receivable))
    r5.metric("存货", format_money(latest_inventory))

    # =====================================================
    # 五、财务排雷
    # =====================================================

    st.header("🚨 五、财务排雷")

    risk_result = analyze_financial_risk(
        operating_cashflow=latest_cashflow,
        net_profit=latest_profit,
        receivable=latest_receivable,
        revenue=latest_revenue,
        inventory=latest_inventory,
        roe=annual_roe,
        debt_ratio=annual_debt
    )

    risk_score = risk_result["score"]

    st.metric(
        "财务风险评分",
        f"{risk_score}/10"
    )

    if risk_result["risk_items"]:
        for item in risk_result["risk_items"]:
            st.warning(f"⚠️ {item}")
    else:
        st.success("✅ 暂未发现明显财务风险")

    # =====================================================
    # 六、5年财务质量
    # =====================================================

    st.header("📈 六、5年财务质量")

    cash_result = risk_result

    financial_quality = calculate_financial_quality(
        trend,
        cash_result["ratio"]
    )

    fq1, fq2 = st.columns(2)

    fq1.metric("财务质量评分", f"{financial_quality['score']}/100")
    fq2.metric("财务质量评级", financial_quality["rating"])

    # =====================================================
    # 七、当前价值估值 V16.5
    # =====================================================

    st.header("💰 七、当前价值估值")

    valuation_model_override = st.selectbox(
        "🧠 估值模型",
        [
            "自动识别",
            "普通成长/制造",
            "银行",
            "保险",
            "券商",
            "周期"
        ],
        index=0,
        key="valuation_model_override"
    )

    valuation_model = detect_valuation_model(
        stock_code=stock_code,
        override=valuation_model_override
    )

    valuation_config = get_valuation_config(
        valuation_model,
        annual_roe=annual_roe
    )

    st.info(
        "🧠 当前估值模型："
        + valuation_config["name"]
        + "｜"
        + valuation_config["method"]
    )

    current_pe = None
    current_pb = None

    if current_price is not None and annual_eps is not None and annual_eps > 0:
        current_pe = current_price / annual_eps

    if current_price is not None and annual_bvps is not None and annual_bvps > 0:
        current_pb = current_price / annual_bvps

    valuation_result = calculate_valuation_scenarios(
        eps=annual_eps,
        bvps=annual_bvps,
        conservative_pe=valuation_config["conservative_pe"],
        normal_pe=valuation_config["normal_pe"],
        optimistic_pe=valuation_config["optimistic_pe"],
        conservative_pb=valuation_config["conservative_pb"],
        normal_pb=valuation_config["normal_pb"],
        optimistic_pb=valuation_config["optimistic_pb"],
        pe_weight=valuation_config["pe_weight"],
        pb_weight=valuation_config["pb_weight"]
    )

    conservative_value = valuation_result["conservative"]
    normal_value = valuation_result["normal"]
    optimistic_value = valuation_result["optimistic"]
    entry_price = valuation_result["entry_price"]
    heavy_price = valuation_result["heavy_price"]

    v1, v2, v3, v4, v5 = st.columns(5)

    v1.metric("当前PE", "暂无" if current_pe is None else f"{current_pe:.2f}")
    v2.metric("当前PB", "暂无" if current_pb is None else f"{current_pb:.2f}")
    v3.metric("保守价值", "暂无" if conservative_value is None else f"{conservative_value:.2f} 元")
    v4.metric("中性合理价", "暂无" if normal_value is None else f"{normal_value:.2f} 元")
    v5.metric("建仓参考价", "暂无" if entry_price is None else f"{entry_price:.2f} 元")

    st.write(
        "乐观价值："
        + ("暂无" if optimistic_value is None else f"{optimistic_value:.2f} 元")
        + " ｜ 重仓参考价："
        + ("暂无" if heavy_price is None else f"{heavy_price:.2f} 元")
    )

    st.caption(valuation_config["note"])

    # =====================================================
    # 八、历史估值
    # =====================================================

    st.header("📊 八、历史PE估值")

    historical_pe = build_historical_pe(
        history,
        trend,
        max_years=10
    )

    historical_stats = calculate_historical_statistics(
        historical_pe,
        current_pe
    )

    historical_level = get_historical_valuation_level(
        historical_stats["percentile"]
    )

    if historical_pe is not None and not historical_pe.empty:

        display_history = historical_pe.copy()

        for column in ["年末收盘价", "EPS", "PE"]:
            display_history[column] = display_history[column].round(2)

        st.dataframe(
            display_history,
            use_container_width=True,
            hide_index=True
        )

        h1, h2, h3 = st.columns(3)

        h1.metric(
            "历史最低PE",
            "暂无" if historical_stats["min"] is None else f"{historical_stats['min']:.2f}"
        )
        h2.metric(
            "历史中位PE",
            "暂无" if historical_stats["median"] is None else f"{historical_stats['median']:.2f}"
        )
        h3.metric(
            "历史最高PE",
            "暂无" if historical_stats["max"] is None else f"{historical_stats['max']:.2f}"
        )

        h4, h5, h6 = st.columns(3)

        h4.metric(
            "历史25%分位",
            "暂无" if historical_stats["q25"] is None else f"{historical_stats['q25']:.2f}"
        )
        h5.metric(
            "历史75%分位",
            "暂无" if historical_stats["q75"] is None else f"{historical_stats['q75']:.2f}"
        )
        h6.metric(
            "当前PE历史分位",
            "暂无" if historical_stats["percentile"] is None else f"{historical_stats['percentile']:.1f}%"
        )

        if historical_stats["deviation"] is not None:
            st.metric(
                "当前PE相对历史中位数偏离",
                f"{historical_stats['deviation']:.2f}%"
            )

        st.write(f"**历史估值区域：{historical_level}**")

        if historical_level == "历史低位":
            st.success("🟢 当前PE处于历史低位区域。")
        elif historical_level == "历史中低位":
            st.success("🟢 当前PE处于历史中低位区域。")
        elif historical_level == "历史中枢":
            st.info("🟡 当前PE接近历史估值中枢。")
        elif historical_level == "历史中高位":
            st.warning("🟠 当前PE处于历史中高位区域。")
        elif historical_level == "历史高位":
            st.error("🔴 当前PE处于历史高位区域。")

    else:
        st.warning("⚠️ 历史PE数据不足。")

    # =====================================================
    # 九、同行业比较 V16.1
    # =====================================================

    st.header("🏭 九、同行业比较")

    auto_peer_result = get_peer_candidates(
        stock_code,
        max_peers=5
    )

    auto_industry = auto_peer_result.get("industry")
    auto_peers = auto_peer_result.get("peers", [])

    if auto_peers:
        st.success(f"✅ 自动识别同行成功：{auto_industry}")
        st.write("自动同行股票：" + "、".join(auto_peers))
        peer_codes = auto_peers
    else:
        st.warning("⚠️ 自动同行识别暂时失败，使用手动同行股票。")
        peer_codes = []
        if peer_input:
            for code in peer_input.split(","):
                clean_code = clean_stock_code(code)
                if clean_code and clean_code != stock_code and clean_code not in peer_codes:
                    peer_codes.append(clean_code)

    if len(peer_codes) > 5:
        peer_codes = peer_codes[:5]
        st.info("同行最多比较5家公司，已自动取前5家。")

    peer_score = None
    peer_rating = "数据不足"

    if len(peer_codes) < 2:
        st.warning("⚠️ 当前没有足够的同行公司。可以在上方手动输入2～5只同行股票。")
    else:
        compare_codes = [stock_code] + peer_codes
        peer_rows = []
        progress = st.progress(0)

        for index, code in enumerate(compare_codes):
            try:
                data = get_company_annual_data(code)
                if data is None:
                    progress.progress((index + 1) / len(compare_codes))
                    continue

                if code == stock_code:
                    peer_market = stock_data["market"]
                    peer_history = stock_data["history"]
                else:
                    peer_stock_data = load_stock_data(code)
                    if peer_stock_data is None:
                        progress.progress((index + 1) / len(compare_codes))
                        continue
                    peer_market = peer_stock_data["market"]
                    peer_history = peer_stock_data["history"]

                name = code
                price = None

                if peer_market:
                    name = peer_market.get("名称", code)
                    price = safe_float(peer_market.get("最新价"))

                if price is None:
                    price = get_latest_price(peer_history)

                eps = data.get("eps")
                bvps = data.get("bvps")

                pe = None
                pb = None

                if price is not None and eps is not None and eps > 0:
                    pe = price / eps

                if price is not None and bvps is not None and bvps > 0:
                    pb = price / bvps

                peer_rows.append({
                    "代码": code,
                    "名称": name,
                    "价格": price,
                    "ROE": data.get("roe"),
                    "营收增长率": data.get("revenue_growth"),
                    "净利润增长率": data.get("profit_growth"),
                    "资产负债率": data.get("debt"),
                    "PE": pe,
                    "PB": pb
                })

            except Exception:
                st.warning(f"{code} 同行数据获取失败。")

            progress.progress((index + 1) / len(compare_codes))

        if len(peer_rows) < 2:
            st.warning("⚠️ 有效同行公司数量不足，本次跳过同行评分，但继续完成后续价值分析。")
        else:
            peer_df = pd.DataFrame(peer_rows)

            st.subheader("📊 同行业核心指标")
            display_peer = peer_df.copy()

            for column in [
                "价格", "ROE", "营收增长率", "净利润增长率",
                "资产负债率", "PE", "PB"
            ]:
                if column in display_peer.columns:
                    display_peer[column] = display_peer[column].apply(
                        lambda x: "暂无" if pd.isna(x) else round(float(x), 2)
                    )

            st.dataframe(
                display_peer,
                use_container_width=True,
                hide_index=True
            )

            summary = build_peer_summary(peer_df)
            if summary is not None and not summary.empty:
                st.subheader("📊 同行平均水平")
                st.dataframe(summary, use_container_width=True, hide_index=True)

            comparison = compare_target_with_average(peer_df, stock_code)
            if comparison:
                st.subheader("🎯 目标公司相对同行")
                st.dataframe(pd.DataFrame(comparison), use_container_width=True, hide_index=True)

            peer_score_result = calculate_peer_score(peer_df, stock_code)
            peer_score = peer_score_result["score"]
            peer_rating = peer_score_result["rating"]

            p1, p2 = st.columns(2)
            p1.metric("同行竞争力", f"{peer_score}/100")
            p2.metric("同行评级", peer_rating)

            if peer_score_result["details"]:
                st.subheader("📋 同行评分明细")
                detail_df = pd.DataFrame(peer_score_result["details"])
                st.dataframe(detail_df, use_container_width=True, hide_index=True)

    # =====================================================
    # 十、综合投资价值评分
    # =====================================================

    st.header("🏆 十、综合投资价值评分")

    valuation_gap = None

    if current_price is not None and normal_value is not None and normal_value > 0:
        valuation_gap = (normal_value / current_price - 1) * 100

    investment_result = calculate_investment_score(
        financial_score=financial_quality["score"],
        peer_score=peer_score,
        valuation_gap=valuation_gap,
        risk_score=risk_score,
        historical_percentile=historical_stats["percentile"]
    )

    investment_score = investment_result["score"]
    investment_rating = investment_result["rating"]

    s1, s2 = st.columns(2)
    s1.metric("投资价值评分", f"{investment_score}/100")
    s2.metric("投资评级", investment_rating)

    st.subheader("📊 100分综合评分明细")

    score_table = pd.DataFrame({
        "分析维度": [
            "财务质量", "同行竞争力", "当前估值", "历史估值", "风险控制"
        ],
        "满分": [30, 25, 20, 15, 10],
        "实际得分": [
            investment_result["financial_component"],
            investment_result["peer_component"],
            investment_result["valuation_component"],
            investment_result["historical_component"],
            investment_result["risk_component"]
        ]
    })

    st.dataframe(score_table, use_container_width=True, hide_index=True)

    if peer_score is not None:
        st.write(f"**同行竞争力原始评分：{peer_score}/100**")
        st.write(f"**同行对综合评分贡献：{investment_result['peer_component']:.1f}/25**")
    else:
        st.caption("同行数据不足，本次综合评分未使用同行竞争力分项。")

    st.write(f"当前估值判断：**{investment_result['valuation_level']}**")
    st.write(f"历史估值判断：**{investment_result['historical_level']}**")
    st.write(f"风险判断：**{investment_result['risk_level']}**")

    # =====================================================
    # 十一、最终投资决策 V16.4
    # =====================================================

    st.header("🎯 十一、最终投资决策")

    decision_result = make_investment_decision(
        investment_score=investment_result["score"],
        valuation_level=investment_result["valuation_level"],
        historical_level=investment_result["historical_level"],
        risk_level=investment_result["risk_level"]
    )

    d1, d2, d3 = st.columns(3)
    d1.metric("投资决策", decision_result["decision"])
    d2.metric("建议操作", decision_result["action"])
    d3.metric("建议仓位", decision_result["position"])

    st.info("💡 决策理由：" + decision_result["reason"])

    # =====================================================
    # 十二、最终投资结论
    # =====================================================

    st.header("🏆 十二、最终投资结论")

    if investment_score >= 85:
        conclusion = "🟢 优质公司 + 估值具有较好吸引力，值得进入长期重点研究名单。"
    elif investment_score >= 75:
        conclusion = "🟢 公司质量较好，当前估值总体合理，值得长期跟踪。"
    elif investment_score >= 65:
        conclusion = "🟡 公司具备一定价值，建议等待更好的安全边际。"
    elif investment_score >= 50:
        conclusion = "🟠 当前投资吸引力一般，不宜仅凭单项指标做决定。"
    else:
        conclusion = "🔴 当前风险收益比较弱，暂不适合作为长期核心资产。"

    st.info(conclusion)

    if risk_result["risk_items"]:
        st.subheader("⚠️ 核心风险")
        for item in risk_result["risk_items"]:
            st.write(f"- {item}")

    # =====================================================
    # 十三、系统诊断
    # =====================================================

    st.header("🛠️ 十三、系统诊断")

    diagnostic = pd.DataFrame({
        "模块": [
            "data.py", "历史行情", "财务指标", "利润表", "资产负债表",
            "现金流量表", "financial.py", "risk.py", "valuation.py",
            "adaptive_valuation.py", "historical_valuation.py", "peer_compare.py",
            "investment_score.py", "investment_decision.py"
        ],
        "状态": [
            "✅",
            "✅" if history is not None else "❌",
            "✅" if indicators is not None else "❌",
            "✅" if profit is not None else "❌",
            "✅" if balance is not None else "❌",
            "✅" if cashflow is not None else "❌",
            "✅", "✅", "✅", "✅",
            "✅" if historical_pe is not None and not historical_pe.empty else "⏳",
            "✅" if peer_score is not None else "⏳",
            "✅", "✅"
        ]
    })

    st.dataframe(
        diagnostic,
        use_container_width=True,
        hide_index=True
    )

st.divider()

st.caption(
    "ValueStock AI V16.5：统一数据中心 + 财务 + 风险 + 行业自适应估值 + "
    "历史估值 + 同行业比较 + 综合投资价值评分。"
)
