"""ValueStock AI fast data layer V20：并发、短超时、TTL缓存，避免页面长时间卡住。"""
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import time
import pandas as pd
import akshare as ak

_STOCK_CACHE={}; _PEER_CACHE={}
STOCK_TTL=300; PEER_TTL=600; FETCH_TIMEOUT=18

def clean_stock_code(code):
    s=str(code or "").strip()
    return s if len(s)==6 and s.isdigit() else ""

def _safe_call(fn):
    try:
        x=fn()
        if x is not None and hasattr(x,"empty") and not x.empty: return x
    except Exception: pass
    return None

def _history(code):
    x=_safe_call(lambda: ak.stock_zh_a_hist(symbol=code,period="daily",start_date="20200101",end_date="20500101",adjust=""))
    if x is None:
        market="sh"+code if code.startswith("6") else "sz"+code
        x=_safe_call(lambda: ak.stock_zh_a_hist_tx(symbol=market,start_date="20200101",end_date="20500101",adjust=""))
    if x is None: return None
    return x.rename(columns={"date":"日期","close":"收盘","open":"开盘","high":"最高","low":"最低","volume":"成交量","amount":"成交额"})

def _indicators(code):
    x=_safe_call(lambda: ak.stock_financial_analysis_indicator(symbol=code))
    if x is None:
        symbol="SH"+code if code.startswith("6") else "SZ"+code
        x=_safe_call(lambda: ak.stock_financial_analysis_indicator_em(symbol=symbol,indicator="按报告期"))
    return x

def _report(code,typ):
    market="sh"+code if code.startswith("6") else "sz"+code
    return _safe_call(lambda: ak.stock_financial_report_sina(stock=market,symbol=typ))

def _market(code,hist):
    name=code
    try:
        from industry import get_stock_name
        name=get_stock_name(code) or code
    except Exception: pass
    price=change=None
    if hist is not None and not hist.empty:
        cc="收盘" if "收盘" in hist.columns else "close"
        try: price=float(hist.iloc[-1][cc])
        except Exception: pass
        if len(hist)>=2:
            try: change=(float(hist.iloc[-1][cc])/float(hist.iloc[-2][cc])-1)*100
            except Exception: pass
    return {"代码":code,"名称":name,"最新价":price,"涨跌幅":change}

def _run_tasks(tasks,workers=5,timeout=FETCH_TIMEOUT):
    out={}
    ex=ThreadPoolExecutor(max_workers=workers)
    fs={ex.submit(fn):key for key,fn in tasks.items()}
    try:
        for f in as_completed(fs,timeout=timeout):
            key=fs[f]
            try: out[key]=f.result()
            except Exception: out[key]=None
    except TimeoutError:
        # 超时模块直接降级，不阻塞整个研究页面。
        pass
    finally:
        for f in fs:
            if not f.done(): f.cancel()
        ex.shutdown(wait=False,cancel_futures=True)
    for key in tasks: out.setdefault(key,None)
    return out

def load_stock_data_fast(code):
    code=clean_stock_code(code)
    if not code: return None
    now=time.time(); cached=_STOCK_CACHE.get(code)
    if cached and now-cached[0]<STOCK_TTL: return cached[1]
    tasks={"history":lambda:_history(code),"indicators":lambda:_indicators(code),"profit":lambda:_report(code,"利润表"),"balance":lambda:_report(code,"资产负债表"),"cashflow":lambda:_report(code,"现金流量表")}
    out={"code":code,**_run_tasks(tasks,workers=5)}
    out["market"]=_market(code,out["history"])
    _STOCK_CACHE[code]=(now,out)
    return out

def get_latest_price(history):
    if history is None or history.empty: return None
    for c in ("收盘","close"):
        if c in history.columns:
            try: return float(history.iloc[-1][c])
            except Exception: pass
    return None

def check_data_completeness(data):
    if not data: return {"score":0,"available":0,"total":7,"level":"无数据"}
    checks=[data.get("market") is not None,data.get("history") is not None,data.get("indicators") is not None,data.get("profit") is not None,data.get("balance") is not None,data.get("cashflow") is not None,data.get("code") is not None]
    n=sum(checks); score=round(n/7*100)
    return {"score":score,"available":n,"total":7,"level":"优秀" if score>=90 else "良好" if score>=75 else "一般" if score>=60 else "较弱"}

def load_peer_snapshots(codes_tuple):
    codes=tuple(sorted(set(codes_tuple or ())))
    if not codes: return {}
    key=",".join(codes); now=time.time(); cached=_PEER_CACHE.get(key)
    if cached and now-cached[0]<PEER_TTL: return cached[1]
    def one(code): return code,_history(code),_indicators(code)
    tasks={f"p{i}":(lambda c=c:one(c)) for i,c in enumerate(codes)}
    raw=_run_tasks(tasks,workers=min(5,max(1,len(codes))))
    out={}
    for v in raw.values():
        try:
            code,h,ind=v; out[code]={"history":h,"indicators":ind,"market":_market(code,h)}
        except Exception: pass
    _PEER_CACHE[key]=(now,out)
    return out
