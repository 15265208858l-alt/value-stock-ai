"""ValueStock AI - 盈利基础 V20
只使用研究流程已加载的数据，估值阶段不重新联网。"""
from __future__ import annotations
import pandas as pd

def _safe_float(v):
    try:
        if v is None: return None
        s=str(v).strip().replace(",","").replace("%","")
        if s in {"","--","None","none","NaN","nan","null","NULL","-"}: return None
        return float(s)
    except Exception: return None

def _find(df,names):
    if df is None or getattr(df,"empty",True): return None
    for n in names:
        if n in df.columns: return n
    norm={str(c).strip().replace("（","(").replace("）",")"):c for c in df.columns}
    for n in names:
        k=str(n).strip().replace("（","(").replace("）",")")
        if k in norm: return norm[k]
    return None

def _series(df,date_names,eps_names):
    if df is None or getattr(df,"empty",True): return pd.DataFrame(columns=["_date","_eps"])
    try:
        dc=_find(df,date_names); ec=_find(df,eps_names)
        if dc is None or ec is None: return pd.DataFrame(columns=["_date","_eps"])
        x=df[[dc,ec]].copy(); x["_date"]=pd.to_datetime(x[dc],errors="coerce"); x["_eps"]=x[ec].apply(_safe_float)
        return x.dropna(subset=["_date","_eps"]).sort_values("_date").drop_duplicates("_date",keep="last")[["_date","_eps"]].reset_index(drop=True)
    except Exception: return pd.DataFrame(columns=["_date","_eps"])

def _cached_profit(stock_code):
    if not stock_code: return None
    try:
        import fast_data
        item=fast_data._STOCK_CACHE.get(str(stock_code).strip())
        if item: return item[1].get("profit")
    except Exception: pass
    return None

def _cached_indicators(stock_code):
    if not stock_code: return None
    try:
        import fast_data
        item=fast_data._STOCK_CACHE.get(str(stock_code).strip())
        if item: return item[1].get("indicators")
    except Exception: pass
    return None

def calculate_earnings_realization_score(operating_cashflow_ratio=None,profit_growth=None,data_confidence="低"):
    score=70.0; cash=_safe_float(operating_cashflow_ratio); growth=_safe_float(profit_growth)
    if cash is not None:
        if cash>=1.0: score+=18
        elif cash>=.8: score+=12
        elif cash>=.6: score+=5
        elif cash>=.4: score-=5
        else: score-=15
    else: score-=8
    if growth is not None:
        if growth>=80: score-=6
        elif growth>=50: score-=3
        elif growth>=30: score-=1
        elif growth>=10: score+=2
        elif growth<0: score-=5
    if data_confidence=="高": score+=4
    elif data_confidence=="低": score-=6
    score=max(40.0,min(95.0,score)); coeff=.55+score/100.0*.43
    level="高" if score>=80 else "中" if score>=65 else "低"
    return {"score":round(score),"coefficient":round(coeff,3),"level":level}

def build_earnings_basis(indicators,annual_eps=None,operating_cashflow_ratio=None,profit_growth=None,stock_code=None,profit_report=None):
    # 优先使用调用方传入的数据；兼容旧主流程时，从刚刚加载的TTL缓存取利润表。
    if profit_report is None: profit_report=_cached_profit(stock_code)
    if (indicators is None or getattr(indicators,"empty",True)) and stock_code: indicators=_cached_indicators(stock_code)
    result={"annual_eps":_safe_float(annual_eps),"latest_eps":None,"prior_same_period_eps":None,"ttm_eps":None,"forward_eps_annualized":None,"normalized_eps":_safe_float(annual_eps),"valuation_eps":_safe_float(annual_eps),"basis":"FY年度EPS","confidence":"低","realization_score":None,"realization_coefficient":None,"realization_level":"低","note":"数据不足，暂使用最近完整年度EPS。","eps_source":"已加载财务数据","latest_report_date":None,"ttm_formula":None}
    report_eps=_series(profit_report,["REPORT_DATE","报告日期","报告期","截止日期","日期"],["基本每股收益","基本每股收益(元)","基本每股收益（元）","基本每股收益(元/股)","基本每股收益（元/股）","每股收益","每股收益(元)","每股收益（元）","EPSJB"])
    ind_eps=_series(indicators,["REPORT_DATE","日期","报告期","报告日期","截止日期"],["BASIC_EPS","基本每股收益(元)","基本每股收益","基本每股收益（元）","EPSJB","EPS","摊薄每股收益(元)","摊薄每股收益","每股收益(元)","每股收益"])
    x=report_eps if not report_eps.empty else ind_eps
    confidence="高" if not x.empty else "低"
    if x.empty:
        r=calculate_earnings_realization_score(operating_cashflow_ratio,profit_growth,"低"); result.update(realization_score=r["score"],realization_coefficient=r["coefficient"],realization_level=r["level"]); return result
    latest=x.iloc[-1]; latest_date=latest["_date"]; latest_eps=_safe_float(latest["_eps"])
    result.update(latest_eps=latest_eps,latest_report_date=latest_date.strftime("%Y-%m-%d"),confidence=confidence,eps_source="已加载利润表" if not report_eps.empty else "已加载财务指标")
    annual=x[x["_date"].dt.month==12]
    if not annual.empty: result["annual_eps"]=_safe_float(annual.iloc[-1]["_eps"])
    annual_eps_value=result["annual_eps"]
    if latest_date.month!=12 and latest_eps is not None and annual_eps_value is not None:
        prior=x[(x["_date"].dt.year==latest_date.year-1)&(x["_date"].dt.month==latest_date.month)]
        if not prior.empty:
            prior_eps=_safe_float(prior.iloc[-1]["_eps"]); result["prior_same_period_eps"]=prior_eps
            if prior_eps is not None:
                ttm=annual_eps_value+latest_eps-prior_eps
                if ttm>0: result.update(ttm_eps=ttm,basis="TTM EPS",ttm_formula=f"{annual_eps_value:.4f} + {latest_eps:.4f} - {prior_eps:.4f}")
    if latest_eps is not None and latest_eps>0:
        mult={3:4.0,6:2.0,9:4.0/3.0,12:1.0}.get(int(latest_date.month))
        if mult is not None: result["forward_eps_annualized"]=latest_eps*mult
    base=result["ttm_eps"] if result["ttm_eps"] is not None else result["annual_eps"]
    r=calculate_earnings_realization_score(operating_cashflow_ratio,profit_growth,confidence)
    result.update(realization_score=r["score"],realization_coefficient=r["coefficient"],realization_level=r["level"])
    if base is not None and base>0:
        annual_base=result["annual_eps"] or base
        normalized=base*r["coefficient"]+annual_base*(1-r["coefficient"])
        if normalized>0:
            result.update(normalized_eps=normalized,valuation_eps=normalized,basis="正常化EPS",note="估值分母采用TTM/年度EPS与盈利兑现系数加权后的正常化EPS；Forward EPS仅作为观察指标。")
    return result
