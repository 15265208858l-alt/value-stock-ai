"""ValueStock AI 数据中心 V1.2"""

import akshare as ak
from functools import lru_cache


def clean_stock_code(code):
    if code is None:
        return ""
    code = str(code).strip()
    return code if len(code) == 6 and code.isdigit() else ""


def get_market_code(stock_code):
    if stock_code.startswith(("6", "68")):
        return "sh" + stock_code
    if stock_code.startswith(("0", "3")):
        return "sz" + stock_code
    if stock_code.startswith(("4", "8")):
        return "bj" + stock_code
    return stock_code


def get_symbol_code(stock_code):
    if stock_code.startswith(("6", "68")):
        return "SH" + stock_code
    if stock_code.startswith(("0", "3")):
        return "SZ" + stock_code
    if stock_code.startswith(("4", "8")):
        return "BJ" + stock_code
    return stock_code


def get_realtime_market(stock_code):
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return None
    try:
        data = ak.stock_zh_a_spot_em()
        if data is None or data.empty:
            return None
        code_col = next((c for c in ["代码", "股票代码"] if c in data.columns), None)
        if code_col is None:
            return None
        result = data[data[code_col].astype(str) == stock_code]
        if result.empty:
            return None
        market = result.iloc[0].to_dict()
        if not market.get("名称") or str(market.get("名称")).strip() in {"None", "nan", ""}:
            try:
                from industry import get_stock_name
                fallback_name = get_stock_name(stock_code)
                if fallback_name:
                    market["名称"] = fallback_name
            except Exception:
                pass
        return market
    except Exception:
        return None


def get_history_data(stock_code, start_date="20200101", end_date="20500101"):
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return None
    try:
        data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, end_date=end_date, adjust="")
        if data is not None and not data.empty:
            return data
    except Exception:
        pass
    try:
        data = ak.stock_zh_a_hist_tx(symbol=get_market_code(stock_code), start_date=start_date, end_date=end_date, adjust="")
        if data is not None and not data.empty:
            return data
    except Exception:
        pass
    return None


def get_latest_price(history):
    if history is None or history.empty:
        return None
    try:
        for col in ["收盘", "close"]:
            if col in history.columns:
                return float(history.iloc[-1][col])
    except Exception:
        pass
    return None


def get_financial_indicators(stock_code):
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return None
    for symbol in [stock_code, get_symbol_code(stock_code)]:
        try:
            data = ak.stock_financial_analysis_indicator(symbol=symbol)
            if data is not None and not data.empty:
                return data
        except Exception:
            pass
    try:
        data = ak.stock_financial_analysis_indicator_em(symbol=stock_code, indicator="按报告期")
        if data is not None and not data.empty:
            return data
    except Exception:
        pass
    return None


def get_financial_report(stock_code, report_type):
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return None
    try:
        data = ak.stock_financial_report_sina(stock=get_market_code(stock_code), symbol=report_type)
        if data is not None and not data.empty:
            return data
    except Exception:
        pass
    return None


@lru_cache(maxsize=32)
def load_stock_data(stock_code):
    """加载并缓存股票基础数据；同一运行进程内重复调用同一股票不会重复访问远端接口。"""
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return None
    return {
        "code": stock_code,
        "market": get_realtime_market(stock_code),
        "history": get_history_data(stock_code),
        "indicators": get_financial_indicators(stock_code),
        "profit": get_financial_report(stock_code, "利润表"),
        "balance": get_financial_report(stock_code, "资产负债表"),
        "cashflow": get_financial_report(stock_code, "现金流量表"),
    }


def check_data_completeness(stock_data):
    if stock_data is None:
        return {"score": 0, "available": 0, "total": 7, "level": "无数据"}
    checks = [
        stock_data.get("market") is not None,
        stock_data.get("history") is not None,
        stock_data.get("indicators") is not None,
        stock_data.get("profit") is not None,
        stock_data.get("balance") is not None,
        stock_data.get("cashflow") is not None,
        stock_data.get("code") is not None,
    ]
    available = sum(checks)
    total = len(checks)
    score = round(available / total * 100)
    level = "优秀" if score >= 90 else "良好" if score >= 75 else "一般" if score >= 60 else "较弱"
    return {"score": score, "available": available, "total": total, "level": level}
