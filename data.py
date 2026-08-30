"""ValueStock AI 数据中心 V1.5

Work OS 共享调用增强版：
1. 多次重试
2. 数据源诊断
3. 单模块失败不影响其他模块
4. 行情/历史数据增加 Sina/Tencent 备用链路
5. 诊断只报告最终未解决的问题；主数据源失败但备用源成功时显示为“已恢复”
6. V17.1.1：三大财务报表并行加载，降低同行比较阶段的等待时间
7. V18 UI bootstrap：从首个已导入模块注入产品视觉层，避免依赖 sitecustomize
"""

import time
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

import akshare as ak

_LAST_ERRORS = {}
_SOURCE_STATUS = {}


def _install_ui_bootstrap():
    """在不改变投资计算逻辑的前提下，把品牌UI注入主程序。

    app.py 会在导入 data.py 后调用 st.set_page_config；因此这里仅做函数包装，
    等主程序正式调用 set_page_config 后再渲染 CSS 和首页品牌区。
    """
    try:
        import streamlit as st
        if getattr(st, "_valuestock_ui_bootstrapped", False):
            return
        original_set_page_config = st.set_page_config
        state = {"rendered": False}

        css = r'''
        <style>
        :root{
          --vs-navy:#14233b; --vs-blue:#2e5a87; --vs-gold:#b8872d;
          --vs-bg:#eef2f6; --vs-card:#ffffff; --vs-border:#d7dee8; --vs-muted:#66758a;
        }
        .stApp,[data-testid="stAppViewContainer"]{background:var(--vs-bg);}
        [data-testid="stHeader"]{background:rgba(238,242,246,.96);}
        .block-container{max-width:1360px;padding-top:1.2rem;padding-bottom:3rem;}
        h1,h2,h3{color:var(--vs-navy)!important;}
        h1{font-size:2rem!important;}
        h2{font-size:1.3rem!important;margin-top:1.25rem!important;padding-bottom:.45rem;border-bottom:1px solid var(--vs-border);}
        [data-testid="stMetric"]{background:#fff;border:1px solid var(--vs-border);border-radius:16px;padding:14px 16px;box-shadow:0 4px 16px rgba(20,35,59,.045);}
        [data-testid="stMetricLabel"]{color:var(--vs-muted)!important;}
        [data-testid="stMetricValue"]{color:var(--vs-navy)!important;font-weight:800;}
        div[data-testid="stDataFrame"]{border:1px solid var(--vs-border);border-radius:14px;overflow:hidden;background:#fff;}
        .stTextInput input,.stSelectbox>div>div{border-radius:12px!important;}
        button[kind="primary"]{border-radius:12px!important;font-weight:800!important;box-shadow:0 6px 18px rgba(184,135,45,.20);}
        .vs-topbar{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:10px 2px 14px;}
        .vs-brand-wrap{display:flex;align-items:center;gap:14px;}
        .vs-logo{width:50px;height:50px;border-radius:14px;background:linear-gradient(145deg,#14233b,#2e5a87);display:flex;align-items:center;justify-content:center;color:#f4d58f;font-weight:900;font-size:17px;box-shadow:0 8px 22px rgba(20,35,59,.18);}
        .vs-brand{font-size:1.65rem;font-weight:850;color:var(--vs-navy);line-height:1.0;}
        .vs-brand-sub{font-size:.82rem;color:var(--vs-muted);margin-top:6px;}
        .vs-status{background:#f4ead7;color:#7d5a16;border:1px solid #e7d5ae;border-radius:999px;padding:6px 11px;font-size:.78rem;font-weight:700;}
        .vs-hero{background:linear-gradient(135deg,#14233b 0%,#274b72 64%,#b8872d 100%);color:#fff;border-radius:24px;padding:34px 36px;margin:4px 0 18px;box-shadow:0 14px 34px rgba(20,35,59,.18);}
        .vs-hero-title{font-size:2.45rem;font-weight:900;}
        .vs-hero-sub{font-size:1.05rem;opacity:.94;margin-top:7px;}
        .vs-hero-slogan{font-size:1.18rem;margin-top:16px;font-weight:650;}
        .vs-chip-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px;}
        .vs-chip{display:inline-flex;padding:6px 11px;border:1px solid rgba(255,255,255,.22);border-radius:999px;background:rgba(255,255,255,.08);font-size:.8rem;}
        .vs-search{background:#fff;border:1px solid var(--vs-border);border-radius:18px;padding:18px 20px;margin-bottom:18px;box-shadow:0 6px 20px rgba(20,35,59,.06);}
        .vs-card{background:#fff;border:1px solid var(--vs-border);border-radius:18px;padding:18px 20px;margin:10px 0;box-shadow:0 5px 18px rgba(20,35,59,.05);}
        .vs-card-title{font-size:1rem;font-weight:800;color:var(--vs-navy);margin-bottom:8px;}
        .vs-muted{color:var(--vs-muted);font-size:.84rem;}
        section[data-testid="stSidebar"]{background:#152740;}
        </style>
        '''

        hero = '''
        <div class="vs-topbar">
          <div class="vs-brand-wrap">
            <div class="vs-logo">A股</div>
            <div>
              <div class="vs-brand">A股价值研投</div>
              <div class="vs-brand-sub">ValueStock AI · A股长期价值投资研究平台</div>
            </div>
          </div>
          <div class="vs-status">🟢 研究系统运行中</div>
        </div>
        <div class="vs-hero">
          <div class="vs-hero-title">让AI帮你看懂一家A股公司</div>
          <div class="vs-hero-sub">财务质量 · 现金流 · 估值 · 历史估值 · 同行业 · 风险排查</div>
          <div class="vs-hero-slogan">用AI研究价值，而不是追逐情绪。</div>
          <div class="vs-chip-row">
            <span class="vs-chip">长期价值投资</span>
            <span class="vs-chip">正常化EPS</span>
            <span class="vs-chip">行业自适应估值</span>
            <span class="vs-chip">安全边际</span>
          </div>
        </div>
        '''

        def patched_set_page_config(*args, **kwargs):
            result = original_set_page_config(*args, **kwargs)
            if not state["rendered"]:
                state["rendered"] = True
                try:
                    st.markdown(css, unsafe_allow_html=True)
                    st.markdown(hero, unsafe_allow_html=True)
                except Exception:
                    pass
            return result

        st.set_page_config = patched_set_page_config
        st._valuestock_ui_bootstrapped = True
    except Exception:
        pass


_install_ui_bootstrap()


def _record_error(module, exc):
    _LAST_ERRORS[module] = f"{type(exc).__name__}: {exc}"
    _SOURCE_STATUS[module] = "失败"


def _clear_error(module):
    _LAST_ERRORS.pop(module, None)
    _SOURCE_STATUS[module] = "正常"


def _mark_recovered(module, source):
    _LAST_ERRORS.pop(module, None)
    _SOURCE_STATUS[module] = f"已恢复（{source}备用源）"


def get_data_diagnostics():
    result = {}
    for key, status in _SOURCE_STATUS.items():
        if status == "正常":
            result[key] = "正常"
        elif status.startswith("已恢复"):
            result[key] = status
        elif key in _LAST_ERRORS:
            result[key] = _LAST_ERRORS[key]
        else:
            result[key] = status
    return result


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
    if data is None or data.empty:
        return None
    try:
        code_col = next((c for c in ["代码", "股票代码", "code", "symbol"] if c in data.columns), None)
        if code_col is None:
            return None
        raw_codes = data[code_col].astype(str).str.strip()
        normalized = raw_codes.str.extract(r"(\d{6})", expand=False).fillna("")
        result = data[normalized == stock_code]
        if result.empty:
            result = data[raw_codes.str[-6:] == stock_code]
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

    data = _call_with_retry("realtime_market", ak.stock_zh_a_spot_em, attempts=2, delay=0.8)
    market = _normalize_spot_result(data, stock_code)
    if market is not None:
        _clear_error("realtime_market")
        return market

    data = _call_with_retry("realtime_sina", ak.stock_zh_a_spot, attempts=2, delay=0.8)
    market = _normalize_spot_result(data, stock_code)
    if market is not None:
        _mark_recovered("realtime_market", "Sina")
        _clear_error("realtime_sina")
        return market

    try:
        from industry import get_stock_name
        name = get_stock_name(stock_code)
        if name:
            _SOURCE_STATUS["realtime_market"] = "部分恢复（仅公司名称）"
            return {"代码": stock_code, "名称": name}
    except Exception as exc:
        _record_error("realtime_name_fallback", exc)
    return None


def _normalize_history(data):
    if data is None or data.empty:
        return None
    rename_map = {}
    for src, dst in [("date", "日期"), ("close", "收盘"), ("open", "开盘"), ("high", "最高"), ("low", "最低"), ("volume", "成交量"), ("amount", "成交额")]:
        if src in data.columns and dst not in data.columns:
            rename_map[src] = dst
    return data.rename(columns=rename_map)


def get_history_data(stock_code, start_date="20200101", end_date="20500101"):
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return None

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

    data = _call_with_retry(
        "history_tx",
        lambda: ak.stock_zh_a_hist_tx(symbol=get_market_code(stock_code), start_date=start_date, end_date=end_date, adjust=""),
        attempts=2,
        delay=0.8,
    )
    data = _normalize_history(data)
    if data is not None:
        _mark_recovered("history_em", "Tencent")
        _clear_error("history_tx")
        return data

    data = _call_with_retry(
        "history_sina",
        lambda: ak.stock_zh_a_daily(symbol=get_market_code(stock_code), start_date=start_date, end_date=end_date, adjust=""),
        attempts=2,
        delay=0.8,
    )
    data = _normalize_history(data)
    if data is not None:
        _mark_recovered("history_em", "Sina")
        _clear_error("history_sina")
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


def _load_report_pair(stock_code, report_type):
    return report_type, get_financial_report(stock_code, report_type)


@lru_cache(maxsize=32)
def load_stock_data(stock_code):
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return None

    result = {
        "code": stock_code,
        "market": get_realtime_market(stock_code),
        "history": get_history_data(stock_code),
        "indicators": get_financial_indicators(stock_code),
        "profit": None,
        "balance": None,
        "cashflow": None,
    }

    report_types = ["利润表", "资产负债表", "现金流量表"]
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(_load_report_pair, stock_code, report_type) for report_type in report_types]
        for future in as_completed(futures):
            try:
                report_type, report_data = future.result()
                if report_type == "利润表":
                    result["profit"] = report_data
                elif report_type == "资产负债表":
                    result["balance"] = report_data
                elif report_type == "现金流量表":
                    result["cashflow"] = report_data
            except Exception as exc:
                _record_error("financial_report_parallel", exc)

    return result


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
