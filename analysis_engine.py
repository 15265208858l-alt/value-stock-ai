# =========================================================
# ValueStock AI - Shared Analysis Engine
# V17.2.1
#
# 核心原则：Work OS 与独立版 ValueStock AI 必须使用同一套计算结果。
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
from peer_compare import calculate_peer_score, build_peer_summary, compare_target_with_average
from investment_score import calculate_investment_score
from investment_decision import make_investment_decision
from industry import get_peer_candidates, get_stock_name


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
    return df.replace({pd.NA: None}).to_dict(orient="records")


def _peer_rows(code, data, peer_codes):
    rows = []
    for pc in [code] + peer_codes[:5]:
        try:
            pdta = data if pc == code else load_stock_data(pc)
            if pdta is None or pdta.get("indicators") is None or pdta["indicators"].empty:
                continue
            pfd = process_financial_indicators(pdta["indicators"])["annual"]
            pm = pdta.get("market") or {}
            pp = sf(pm.get("最新价")) or get_latest_price(pdta.get("history"))
            pe = None if pp is None or pfd.get("eps") in {None, 0} else pp / pfd["eps"]
            pbt = None if pp is None or pfd.get("bvps") in {None, 0} else pp / pfd["bvps"]
            pname = pm.get("名称") or get_stock_name(pc) or pc
            rows.append({
                "代码": pc,
                "名称": pname,
                "价格": pp,
                "ROE": pfd.get("roe"),
                "营收增长率": pfd.get("revenue_growth"),
                "净利润增长率": pfd.get("profit_growth"),
                "PE": pe,
                "PB": pbt,
                "资产负债率": pfd.get("debt"),
            })
        except Exception:
            continue
    return rows


def analyze_stock(stock_code: str, peer_input: str = "", override: str = "自动识别") -> dict:
    """与独立版 ValueStock AI 使用同一套核心计算，返回稳定、完整、兼容UI的结构。"""
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

    risk = analyze_financial_risk(rv["ocf"], rv["net_profit"], rv["receivable"], rv["revenue"], rv["inventory"], annual_roe, annual_debt)
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

    auto = get_peer_candidates(code, max_peers=5)
    peer_codes = auto.get("peers", []) if auto else []
    if not peer_codes and code == "601318":
        peer_codes = ["601601", "601336"]
        auto = {"industry": "保险"}
    if not peer_codes and peer_input:
        peer_codes = [clean_stock_code(x) for x in peer_input.split(",") if clean_stock_code(x) and clean_stock_code(x) != code]

    rows = _peer_rows(code, data, peer_codes) if len(peer_codes) >= 2 else []
    peer_score = None
    peer_result = None
    peer_summary = []
    peer_compare = []
    if len(rows) >= 2:
        pdf = pd.DataFrame(rows)
        peer_summary_df = build_peer_summary(pdf)
        peer_summary = _records(peer_summary_df)
        peer_compare = compare_target_with_average(pdf, code)
        peer_result = calculate_peer_score(pdf, code)
        peer_score = peer_result.get("score") if peer_result else None

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

    # ---------------------------------------------------------
    # 统一数据契约：Work OS 与独立版 UI 使用这些字段，避免再次出现
    # “真实计算已经完成，但上层页面全部显示暂无”的问题。
    # ---------------------------------------------------------
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

    peer_payload = {
        "industry": auto.get("industry") if auto else None,
        "codes": peer_codes[:5],
        "peers": peer_codes[:5],
        "rows": rows,
        "summary": peer_summary,
        "compare": peer_compare,
        "score": peer_score,
        "rating": peer_result.get("rating") if peer_result else "数据不足",
        "result": peer_result,
    }

    return {
        "success": True,
        "engine": "ValueStock AI V17.2.1 Shared Engine",
        "code": code,
        "name": name,
        "industry": auto.get("industry") if auto else None,
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
        "peer": peer_payload,
        "investment_score": score,
        "investment": investment,
        "decision": decision,
        "conclusion": conclusion,
    }
