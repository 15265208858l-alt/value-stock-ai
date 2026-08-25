"""ValueStock AI 数据中心 V1.3

为 Work OS 共享调用增加：
1. 多次重试
2. 数据源诊断
3. 单模块失败不影响其他模块
"""

import time
from functools import lru_cache

import akshare as ak

_LAST_ERRORS = {}


def _record_error(module, exc):
    _LAST_ERRORS[module] = f"{type(exc).__name__}: {exc}"


def get_data_diagnostics():
    return dict(_LAST_ERRORS)


def _call_with_retry(name, func, attempts=3, delay=1.2):
    last_exc = None
    for i in range(attempts):
        try:
            result = func()
            if result is not None:
                try:
                    if not result.empty:
                        _LAST_ERRORS.pop(name, None)
                        return result
                except AttributeError:
                    _LAST_ERRORS.pop(name, None)
                    return result
            last_exc = RuntimeError("返回空数据")
        except Exception as exc:
            last_exc = exc
        if i < attempts - 1:
            time.sleep(delay * (i + 1))
    if last_exc:
        _record_error(name, last_exc)
    return None


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
    data = _call_with_retry("realtime_market", ak.stock_zh_a_spot_em, attempts=3)
    if data is None or data.empty:
        return None
    try:
        code_col = next((c for c in ["代码", "股票代码"] if c in data.columns), None)
        if code_col is None:
            _record_error("realtime_market", RuntimeError(f"找不到股票代码字段，实际字段：{list(data.columns)[:20]}"))
            return None
        result = data[data[code_col].astype(str).str.zfill(6) == stock_code]
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
    except Exception as exc:
        _record_error("realtime_market_parse", exc)
        return None


def get_history_data(stock_code, start_date="20200101", end_date="20500101"):
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return None
    data = _call_with_retry(
        "history_em",
        lambda: ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, end_date=end_date, adjust=""),
        attempts=2,
    )
    if data is not None:
        return data
    return _call_with_retry(
        "history_tx",
        lambda: ak.stock_zh_a_hist_tx(symbol=get_market_code(stock_code), start_date=start_date, end_date=end_date, adjust=""),
        attempts=2,
    )


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
        data = _call_with_retry(
            f"financial_indicators_{symbol}",
            lambda symbol=symbol: ak.stock_financial_analysis_indicator(symbol=symbol),
            attempts=2,
        )
        if data is not None:
            return data
    return _call_with_retry(
        "financial_indicators_em",
        lambda: ak.stock_financial_analysis_indicator_em(symbol=stock_code, indicator="按报告期"),
        attempts=2,
    )


def get_financial_report(stock_code, report_type):
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return None
    return _call_with_retry(
        f"financial_report_{report_type}",
        lambda: ak.stock_financial_report_sina(stock=get_market_code(stock_code), symbol=report_type),
        attempts=2,
    )


@lru_cache(maxsize=32)
def load_stock_data(stock_code):
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
