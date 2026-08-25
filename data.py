"""ValueStock AI 数据中心 V1.4

Work OS 共享调用增强版：
1. 多次重试
2. 数据源诊断
3. 单模块失败不影响其他模块
4. 行情/历史数据增加 Sina/Tencent 备用链路
5. 不再因为 Eastmoney 连接被远端主动断开而直接判定无数据
"""

import time
from functools import lru_cache

import akshare as ak

_LAST_ERRORS = {}


def _record_error(module, exc):
    _LAST_ERRORS[module] = f"{type(exc).__name__}: {exc}"


def _clear_error(module):
    _LAST_ERRORS.pop(module, None)


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
                        _clear_error(name)
                        return result
                except AttributeError:
                    _clear_error(name)
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


def _normalize_spot_result(data, stock_code):
    """统一不同行情源的字段，保证上层 analysis_engine 不需要改。"""
    if data is None or data.empty:
        return None
    try:
        code_col = next((c for c in ["代码", "股票代码", "code", "symbol"] if c in data.columns), None)
        if code_col is None:
            return None
        result = data[data[code_col].astype(str).str.replace("[A-Za-z]", "", regex=True).str.zfill(6) == stock_code]
        if result.empty:
            # Sina 有时返回 sh600xxx / sz000xxx
            result = data[data[code_col].astype(str).str[-6:] == stock_code]
        if result.empty:
            return None
        market = result.iloc[0].to_dict()
        if "名称" not in market:
            for candidate in ["name", "股票名称"]:
                if candidate in market:
                    market["名称"] = market[candidate]
                    break
        if "最新价" not in market:
            for candidate in ["trade", "现价", "price"]:
                if candidate in market:
                    market["最新价"] = market[candidate]
                    break
        if "涨跌幅" not in market:
            for candidate in ["changepercent", "涨跌幅(%)", "change_percent"]:
                if candidate in market:
                    market["涨跌幅"] = market[candidate]
                    break
        if "成交额" not in market:
            for candidate in ["amount", "成交额"]:
                if candidate in market:
                    market["成交额"] = market[candidate]
                    break
        return market
    except Exception:
        return None


def get_realtime_market(stock_code):
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return None

    # ① Eastmoney：保留原有主链路
    data = _call_with_retry("realtime_market", ak.stock_zh_a_spot_em, attempts=2, delay=0.8)
    market = _normalize_spot_result(data, stock_code)
    if market is not None:
        _clear_error("realtime_market")
        return market

    # ② Sina：只取 A 股实时行情，避免 Eastmoney 全市场接口被远端断开
    data = _call_with_retry("realtime_sina", ak.stock_zh_a_spot, attempts=2, delay=0.8)
    market = _normalize_spot_result(data, stock_code)
    if market is not None:
        _clear_error("realtime_market")
        return market

    # ③ 名称兜底，不阻塞整个分析
    try:
        from industry import get_stock_name
        name = get_stock_name(stock_code)
        if name:
            return {"代码": stock_code, "名称": name}
    except Exception as exc:
        _record_error("realtime_name_fallback", exc)
    return None


def _normalize_history(data):
    if data is None or data.empty:
        return None
    # 上层统一使用“日期、收盘”等字段。不同源保持原字段也可以，
    # 这里仅把常见英文列名映射到中文列名。
    rename_map = {}
    for src, dst in [("date", "日期"), ("close", "收盘"), ("open", "开盘"), ("high", "最高"), ("low", "最低"), ("volume", "成交量"), ("amount", "成交额")]:
        if src in data.columns and dst not in data.columns:
            rename_map[src] = dst
    return data.rename(columns=rename_map)


def get_history_data(stock_code, start_date="20200101", end_date="20500101"):
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return None

    # ① Eastmoney
    data = _call_with_retry(
        "history_em",
        lambda: ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, end_date=end_date, adjust=""),
        attempts=2,
        delay=0.8,
    )
    data = _normalize_history(data)
    if data is not None:
        _clear_error("history_em")
        return data

    # ② Tencent：按市场代码请求
    data = _call_with_retry(
        "history_tx",
        lambda: ak.stock_zh_a_hist_tx(symbol=get_market_code(stock_code), start_date=start_date, end_date=end_date, adjust=""),
        attempts=2,
        delay=0.8,
    )
    data = _normalize_history(data)
    if data is not None:
        _clear_error("history_em")
        return data

    # ③ Sina 日线：作为第二备用链路
    data = _call_with_retry(
        "history_sina",
        lambda: ak.stock_zh_a_daily(symbol=get_market_code(stock_code), start_date=start_date, end_date=end_date, adjust=""),
        attempts=2,
        delay=0.8,
    )
    data = _normalize_history(data)
    if data is not None:
        _clear_error("history_em")
        return data

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
