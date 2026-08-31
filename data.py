"""ValueStock AI 数据中心 V1.6

性能稳定版：
1. 首次研究时把行情、历史行情、财务指标、三大报表并行加载
2. 移除慢速的全市场实时行情扫描，当前价格/涨跌幅直接由历史行情计算
3. 公司名称优先使用本地行业映射，避免额外网络请求
4. 三大报表继续并行
5. 保留失败重试与备用链路
"""

import time
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

import akshare as ak

_LAST_ERRORS = {}
_SOURCE_STATUS = {}


def _install_ui_bootstrap():
    """注入产品视觉层，不改变投资计算逻辑。"""
    try:
        import streamlit as st
        if getattr(st, "_valuestock_ui_bootstrapped", False):
            return
        original_set_page_config = st.set_page_config
        state = {"rendered": False}
        css = r'''
        <style>
        :root{--vs-navy:#14233b;--vs-blue:#2e5a87;--vs-gold:#b8872d;--vs-bg:#eef2f6;--vs-card:#fff;--vs-border:#d7dee8;--vs-muted:#66758a;}
        .stApp,[data-testid="stAppViewContainer"]{background:var(--vs-bg);}
        [data-testid="stHeader"]{background:rgba(238,242,246,.96);}
        .block-container{max-width:1360px;padding-top:1.2rem;padding-bottom:3rem;}
        h1,h2,h3{color:var(--vs-navy)!important;} h1{font-size:2rem!important;} h2{font-size:1.3rem!important;margin-top:1.25rem!important;padding-bottom:.45rem;border-bottom:1px solid var(--vs-border);}
        [data-testid="stMetric"]{background:#fff;border:1px solid var(--vs-border);border-radius:16px;padding:14px 16px;box-shadow:0 4px 16px rgba(20,35,59,.045);}
        [data-testid="stMetricLabel"]{color:var(--vs-muted)!important;} [data-testid="stMetricValue"]{color:var(--vs-navy)!important;font-weight:800;}
        div[data-testid="stDataFrame"]{border:1px solid var(--vs-border);border-radius:14px;overflow:hidden;background:#fff;}
        .stTextInput input,.stSelectbox>div>div{border-radius:12px!important;}
        button[kind="primary"]{border-radius:12px!important;font-weight:800!important;box-shadow:0 6px 18px rgba(184,135,45,.20);}
        .vs-topbar{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:10px 2px 14px;}
        .vs-brand-wrap{display:flex;align-items:center;gap:14px;}.vs-logo{width:50px;height:50px;border-radius:14px;background:linear-gradient(145deg,#14233b,#2e5a87);display:flex;align-items:center;justify-content:center;color:#f4d58f;font-weight:900;font-size:17px;box-shadow:0 8px 22px rgba(20,35,59,.18);}.vs-brand{font-size:1.65rem;font-weight:850;color:var(--vs-navy);line-height:1.0;}.vs-brand-sub{font-size:.82rem;color:var(--vs-muted);margin-top:6px;}.vs-status{background:#f4ead7;color:#7d5a16;border:1px solid #e7d5ae;border-radius:999px;padding:6px 11px;font-size:.78rem;font-weight:700;}
        .vs-hero{background:linear-gradient(135deg,#14233b 0%,#274b72 64%,#b8872d 100%);color:#fff;border-radius:24px;padding:34px 36px;margin:4px 0 18px;box-shadow:0 14px 34px rgba(20,35,59,.18);}.vs-hero-title{font-size:2.45rem;font-weight:900;}.vs-hero-sub{font-size:1.05rem;opacity:.94;margin-top:7px;}.vs-hero-slogan{font-size:1.18rem;margin-top:16px;font-weight:650;}.vs-chip-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px;}.vs-chip{display:inline-flex;padding:6px 11px;border:1px solid rgba(255,255,255,.22);border-radius:999px;background:rgba(255,255,255,.08);font-size:.8rem;}
        section[data-testid="stSidebar"]{background:#152740;}
        </style>
        '''
        hero='''<div class="vs-topbar"><div class="vs-brand-wrap"><div class="vs-logo">A股</div><div><div class="vs-brand">A股价值研投</div><div class="vs-brand-sub">ValueStock AI · A股长期价值投资研究平台</div></div></div><div class="vs-status">🟢 研究系统运行中</div></div><div class="vs-hero"><div class="vs-hero-title">让AI帮你看懂一家A股公司</div><div class="vs-hero-sub">财务质量 · 现金流 · 估值 · 历史估值 · 同行业 · 风险排查</div><div class="vs-hero-slogan">用AI研究价值，而不是追逐情绪。</div><div class="vs-chip-row"><span class="vs-chip">长期价值投资</span><span class="vs-chip">正常化EPS</span><span class="vs-chip">行业自适应估值</span><span class="vs-chip">安全边际</span></div></div>'''
        def patched_set_page_config(*args, **kwargs):
            result=original_set_page_config(*args, **kwargs)
            if not state["rendered"]:
                state["rendered"]=True
                try:
                    st.markdown(css,unsafe_allow_html=True); st.markdown(hero,unsafe_allow_html=True)
                except Exception: pass
            return result
        st.set_page_config=patched_set_page_config
        st._valuestock_ui_bootstrapped=True
    except Exception:
        pass


_install_ui_bootstrap()


def _record_error(module, exc):
    _LAST_ERRORS[module]=f"{type(exc).__name__}: {exc}"
    _SOURCE_STATUS[module]="失败"


def _clear_error(module):
    _LAST_ERRORS.pop(module,None); _SOURCE_STATUS[module]="正常"


def _mark_recovered(module, source):
    _LAST_ERRORS.pop(module,None); _SOURCE_STATUS[module]=f"已恢复（{source}备用源）"


def get_data_diagnostics():
    result={}
    for key,status in _SOURCE_STATUS.items():
        if status=="正常" or status.startswith("已恢复"):
            result[key]=status
        elif key in _LAST_ERRORS:
            result[key]=_LAST_ERRORS[key]
        else:
            result[key]=status
    return result


def _call_with_retry(name, func, attempts=2, delay=0.4):
    last_exc=None
    for i in range(attempts):
        try:
            result=func()
            if result is not None:
                try:
                    if not result.empty:
                        _clear_error(name); return result
                except AttributeError:
                    _clear_error(name); return result
            last_exc=RuntimeError("返回空数据")
        except Exception as exc:
            last_exc=exc
        if i < attempts-1:
            time.sleep(delay*(i+1))
    if last_exc: _record_error(name,last_exc)
    return None


def clean_stock_code(code):
    if code is None: return ""
    code=str(code).strip()
    return code if len(code)==6 and code.isdigit() else ""


def get_market_code(stock_code):
    if stock_code.startswith(("6","68")): return "sh"+stock_code
    if stock_code.startswith(("0","3")): return "sz"+stock_code
    if stock_code.startswith(("4","8")): return "bj"+stock_code
    return stock_code


def get_symbol_code(stock_code):
    if stock_code.startswith(("6","68")): return "SH"+stock_code
    if stock_code.startswith(("0","3")): return "SZ"+stock_code
    if stock_code.startswith(("4","8")): return "BJ"+stock_code
    return stock_code


def _normalize_history(data):
    if data is None or data.empty: return None
    rename_map={}
    for src,dst in [("date","日期"),("close","收盘"),("open","开盘"),("high","最高"),("low","最低"),("volume","成交量"),("amount","成交额")]:
        if src in data.columns and dst not in data.columns: rename_map[src]=dst
    return data.rename(columns=rename_map)


def get_history_data(stock_code,start_date="20200101",end_date="20500101"):
    stock_code=clean_stock_code(stock_code)
    if not stock_code: return None
    data=_call_with_retry("history_em",lambda:ak.stock_zh_a_hist(symbol=stock_code,period="daily",start_date=start_date,end_date=end_date,adjust=""),attempts=2,delay=0.35)
    data=_normalize_history(data)
    if data is not None: _clear_error("history_em"); return data
    data=_call_with_retry("history_tx",lambda:ak.stock_zh_a_hist_tx(symbol=get_market_code(stock_code),start_date=start_date,end_date=end_date,adjust=""),attempts=1,delay=0.2)
    data=_normalize_history(data)
    if data is not None: _mark_recovered("history_em","Tencent"); return data
    data=_call_with_retry("history_sina",lambda:ak.stock_zh_a_daily(symbol=get_market_code(stock_code),start_date=start_date,end_date=end_date,adjust=""),attempts=1,delay=0.2)
    data=_normalize_history(data)
    if data is not None: _mark_recovered("history_em","Sina"); return data
    return None


def get_latest_price(history):
    if history is None or history.empty: return None
    try:
        for col in ["收盘","close"]:
            if col in history.columns: return float(history.iloc[-1][col])
    except Exception: pass
    return None


def _build_market_from_history(stock_code,history):
    """快速行情：不再扫描全市场，只使用历史行情最后两根K线。"""
    try:
        from industry import get_stock_name
        name=get_stock_name(stock_code) or stock_code
    except Exception:
        name=stock_code
    price=get_latest_price(history)
    change=None
    if history is not None and not history.empty and len(history)>=2:
        try:
            close_col="收盘" if "收盘" in history.columns else "close"
            p0=float(history.iloc[-2][close_col]); p1=float(history.iloc[-1][close_col])
            if p0: change=(p1/p0-1)*100
        except Exception: pass
    if price is None: return None
    _clear_error("realtime_market")
    return {"代码":stock_code,"名称":name,"最新价":price,"涨跌幅":change}


def get_realtime_market(stock_code):
    """兼容旧调用；不再请求全市场实时行情。"""
    stock_code=clean_stock_code(stock_code)
    if not stock_code: return None
    return None


def get_financial_indicators(stock_code):
    stock_code=clean_stock_code(stock_code)
    if not stock_code: return None
    data=_call_with_retry(f"financial_indicators_{stock_code}",lambda:ak.stock_financial_analysis_indicator(symbol=stock_code),attempts=2,delay=0.35)
    if data is not None: return data
    return _call_with_retry("financial_indicators_em",lambda:ak.stock_financial_analysis_indicator_em(symbol=stock_code,indicator="按报告期"),attempts=1,delay=0.2)


def get_financial_report(stock_code,report_type):
    stock_code=clean_stock_code(stock_code)
    if not stock_code: return None
    return _call_with_retry(f"financial_report_{report_type}",lambda:ak.stock_financial_report_sina(stock=get_market_code(stock_code),symbol=report_type),attempts=2,delay=0.35)


def _load_report_pair(stock_code,report_type):
    return report_type,get_financial_report(stock_code,report_type)


@lru_cache(maxsize=32)
def load_stock_data(stock_code):
    """核心性能优化：所有互不依赖的数据源并行加载。"""
    stock_code=clean_stock_code(stock_code)
    if not stock_code: return None
    result={"code":stock_code,"market":None,"history":None,"indicators":None,"profit":None,"balance":None,"cashflow":None}
    tasks={
        "history":lambda:get_history_data(stock_code),
        "indicators":lambda:get_financial_indicators(stock_code),
        "profit":lambda:get_financial_report(stock_code,"利润表"),
        "balance":lambda:get_financial_report(stock_code,"资产负债表"),
        "cashflow":lambda:get_financial_report(stock_code,"现金流量表"),
    }
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map={executor.submit(fn):key for key,fn in tasks.items()}
        for future in as_completed(future_map):
            key=future_map[future]
            try: result[key]=future.result()
            except Exception as exc: _record_error(f"load_{key}",exc)
    result["market"]=_build_market_from_history(stock_code,result.get("history"))
    return result


def check_data_completeness(stock_data):
    if stock_data is None: return {"score":0,"available":0,"total":7,"level":"无数据"}
    checks=[stock_data.get("market") is not None,stock_data.get("history") is not None,stock_data.get("indicators") is not None,stock_data.get("profit") is not None,stock_data.get("balance") is not None,stock_data.get("cashflow") is not None,stock_data.get("code") is not None]
    available=sum(checks); total=len(checks); score=round(available/total*100)
    level="优秀" if score>=90 else "良好" if score>=75 else "一般" if score>=60 else "较弱"
    return {"score":score,"available":available,"total":total,"level":level}
