# =========================================================
# ValueStock AI - Shared Analysis Engine
# V17.2.2
#
# Work OS 专用说明：
# - 保留原有财务、风险、估值、历史估值、成长质量、综合评分、决策能力。
# - 移除“同行业比较”执行模块，减少额外外部数据请求与等待时间。
# - 不影响 ValueStock 独立版 app.py；这里只调整共享分析引擎。
# =========================================================

from __future__ import annotations

import pandas as pd

from data import clean_stock_code, load_stock_data, check_data_completeness, get_latest_price
from financial import process_financial_indicators, calculate_financial_quality
from risk import analyze_financial_risk
from valuation import calculate_valuation_scenarios
from adaptive_valuation import detect_valuation_model, get_valuation_config
from earnings_basis import build_earnings_basis
from growth_quality import calculate_growth_quality, get_dynamic_growth_pe
from historical_valuation import build_historical_pe, calculate_historical_statistics, get_historical_valuation_level
from investment_score import calculate_investment_score
from investment_decision import make_investment_decision
from industry import get_stock_name


def sf(v):
    try:
        if v is None or str(v).strip() in {"", "--", "None", "none", "nan", "NaN"}:
            return None
        return float(str(v).replace(",", "").replace("%", ""))
    except Exception:
        return None


def lastv(df, names):
    if df is None or df.empty:
        return None
    for name in names:
        if name in df.columns:
            return sf(df.iloc[0][name])
    return None


def _records(df):
    if df is None or df.empty:
        return []
    try:
        return df.where(pd.notna(df), None).to_dict(orient="records")
    except Exception:
        return df.to_dict(orient="records")


def analyze_stock(stock_code: str, peer_input: str = "", override: str = "自动识别") -> dict:
    """与独立版 ValueStock AI 使用同一套核心计算，但共享版不执行同行业比较。"""
    code = clean_stock_code(stock_code)
    if not code:
        return {"success": False, "error": "请输入6位股票代码。"}

    data = load_stock_data(code)
    if data is None:
        return {"success": False, "error": "股票数据加载失败。"}

    dc = check_data_completeness(data)
    market, history = data.get("market"), data.get("history")
    name = code
    price = chg = dyn_pe = None

    if market:
        name = market.get("名称", code)
        price = sf(market.get("最新价"))
        chg = sf(market.get("涨跌幅"))
        dyn_pe = sf(market.get("市盈率-动态"))

    if price is None:
        price = get_latest_price(history)

    indicators = data.get("indicators")
    if indicators is None or indicators.empty:
        return {"success": False, "error": "财务指标获取失败。"}

    fd = process_financial_indicators(indicators)
    latest, annual, trend = fd["latest"], fd["annual"], fd["trend"]
    annual_roe = annual.get("roe")
    annual_eps = annual.get("eps")
    annual_bvps = annual.get("bvps")
    annual_debt = annual.get("debt")

    rv = {
        "revenue": lastv(data.get("profit"), ["营业总收入", "营业收入", "一、营业总收入"]),
        "net_profit": lastv(data.get("profit"), ["归属于母公司所有者的净利润", "归属于母公司股东的净利润", "净利润", "五、净利润"]),
        "receivable": lastv(data.get("balance"), ["应收账款", "应收款项"]),
        "inventory": lastv(data.get("balance"), ["存货"]),
        "ocf": lastv(data.get("cashflow"), ["经营活动产生的现金流量净额", "经营活动现金流量净额"]),
    }

    risk = analyze_financial_risk(
        rv["ocf"], rv["net_profit"], rv["receivable"], rv["revenue"],
        rv["inventory"], annual_roe, annual_debt
    )
    risk_score = risk.get("score", 5)
    cash_ratio = None if rv["ocf"] is None or rv["net_profit"] in {None, 0} else rv["ocf"] / rv["net_profit"]
    fq = calculate_financial_quality(trend, cash_ratio)

    model = detect_valuation_model(stock_code=code, override=override)
    cfg = dict(get_valuation_config(model, annual_roe=annual_roe))

    earn = build_earnings_basis(
        indicators=indicators,
        annual_eps=annual_eps,
        operating_cashflow_ratio=cash_ratio,
        profit_growth=latest.get("profit_growth"),
    )
    normalized_eps = earn.get("normalized_eps")
    valuation_eps = normalized_eps or annual_eps
    annual_pe = None if price is None or annual_eps is None or annual_eps <= 0 else price / annual_eps

    hist = build_historical_pe(history, trend, max_years=10)
    hs = calculate_historical_statistics(hist, annual_pe)

    if model == "growth_tech":
        gq = calculate_growth_quality(
            revenue_growth=latest.get("revenue_growth"),
            profit_growth=latest.get("profit_growth"),
            roe=latest.get("roe") if latest.get("roe") is not None else annual_roe,
            cashflow_ratio=cash_ratio,
            ttm_eps=earn.get("ttm_eps"),
            annual_eps=annual_eps,
            historical_percentile=hs.get("percentile"),
        )
        dynamic_pe = get_dynamic_growth_pe(
            gq["score"],
            historical_percentile=hs.get("percentile"),
            cashflow_ratio=cash_ratio,
        )
        cfg["conservative_pe"] = dynamic_pe["conservative_pe"]
        cfg["normal_pe"] = dynamic_pe["normal_pe"]
        cfg["optimistic_pe"] = dynamic_pe["optimistic_pe"]
    else:
        gq = None

    valuation_pe = None if price is None or valuation_eps is None or valuation_eps <= 0 else price / valuation_eps
    pb = None if price is None or annual_bvps is None or annual_bvps <= 0 else price / annual_bvps

    vr = calculate_valuation_scenarios(
        eps=valuation_eps,
        bvps=annual_bvps,
        conservative_pe=cfg["conservative_pe"],
        normal_pe=cfg["normal_pe"],
        optimistic_pe=cfg["optimistic_pe"],
        conservative_pb=cfg["conservative_pb"],
        normal_pb=cfg["normal_pb"],
        optimistic_pb=cfg["optimistic_pb"],
        pe_weight=cfg["pe_weight"],
        pb_weight=cfg["pb_weight"],
    )

    # 同行业比较已移除：peer_score 设为 None，由综合评分模块按缺失项自动处理。
    peer_score = None

    gap = None if price is None or vr["normal"] is None or vr["normal"] <= 0 else (vr["normal"] / price - 1) * 100
    score = calculate_investment_score(
        financial_score=fq["score"],
        peer_score=peer_score,
        valuation_gap=gap,
        risk_score=risk_score,
        historical_percentile=hs.get("percentile"),
    )

    decision = make_investment_decision(
        investment_score=score["score"],
        valuation_level=score["valuation_level"],
        historical_level=score["historical_level"],
        risk_level=score["risk_level"],
    )

    if score["score"] >= 85:
        conclusion = "🟢 公司质量与估值较匹配，值得重点研究。"
    elif score["score"] >= 75:
        conclusion = "🟢 公司质量较好，值得长期跟踪。"
    elif score["score"] >= 65:
        conclusion = "🟡 公司具备一定价值，建议等待更好的安全边际。"
    elif score["score"] >= 50:
        conclusion = "🟠 当前投资吸引力一般，建议进一步观察。"
    else:
        conclusion = "🔴 当前风险收益比较弱，暂不适合作为长期核心资产。"

    investment = {
        "score": score.get("score"),
        "rating": score.get("rating"),
        "valuation_level": score.get("valuation_level"),
        "historical_level": score.get("historical_level"),
        "risk_level": score.get("risk_level"),
        "data_confidence": score.get("data_confidence"),
        "decision": decision.get("decision"),
        "action": decision.get("action"),
        "position": decision.get("position"),
        "reason": decision.get("reason"),
    }

    valuation = {
        "model": cfg,
        "earnings": earn,
        "annual_eps": annual_eps,
        "ttm_eps": earn.get("ttm_eps"),
        "normalized_eps": normalized_eps,
        "annual_pe": annual_pe,
        "valuation_pe": valuation_pe,
        "pb": pb,
        "conservative": vr.get("conservative"),
        "normal": vr.get("normal"),
        "optimistic": vr.get("optimistic"),
        "entry_price": vr.get("entry_price"),
        "heavy_price": vr.get("heavy_price"),
        "scenarios": vr,
        "historical_level": get_historical_valuation_level(hs.get("percentile")),
        "historical_percentile": hs.get("percentile"),
        "historical": hs,
        "growth_quality": gq,
    }

    return {
        "success": True,
        "engine": "ValueStock AI V17.2.2 Shared Engine",
        "code": code,
        "name": name or get_stock_name(code) or code,
        "industry": get_stock_name(code) and None,
        "data_center": dc,
        "market": {
            "name": name,
            "price": price,
            "change_pct": chg,
            "dynamic_pe": dyn_pe,
            "history_available": history is not None,
        },
        "financial": {
            "latest": latest,
            "annual": annual,
            "trend": _records(trend),
            "quality": fq,
            "report": rv,
        },
        "risk": {
            **risk,
            "items": risk.get("risk_items", []),
        },
        "valuation": valuation,
        "investment_score": score,
        "investment": investment,
        "decision": decision,
        "conclusion": conclusion,
        "peer": {
            "enabled": False,
            "score": None,
            "rating": "已关闭",
        },
    }
