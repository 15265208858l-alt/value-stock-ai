"""历史PE估值模块 V1.1：兼容不同财务字段，并支持新上市公司。"""
import pandas as pd

def safe_float(value):
    try:
        if value is None: return None
        s=str(value).strip().replace(",","").replace("%","")
        if s in {"","--","None","none","NaN","nan"}: return None
        return float(s)
    except Exception:
        return None

def _date_col(df):
    if df is None or getattr(df,"empty",True): return None
    for c in ["日期","date","REPORT_DATE","报告期","报告日期","截止日期"]:
        if c in df.columns: return c
    return None

def _eps_col(df):
    if df is None or getattr(df,"empty",True): return None
    names=["EPS","基本每股收益","基本每股收益(元)","基本每股收益（元）","基本每股收益(元/股)","基本每股收益（元/股）","EPSJB","每股收益","每股收益(元)","每股收益（元）","摊薄每股收益(元)","摊薄每股收益","EPSXS"]
    return next((c for c in names if c in df.columns),None)

def prepare_price_data(history):
    if history is None or history.empty: return pd.DataFrame()
    df=history.copy(); dc=_date_col(df)
    if dc is None: return pd.DataFrame()
    pc=next((c for c in ["收盘","close","年末收盘价"] if c in df.columns),None)
    if pc is None: return pd.DataFrame()
    df["_日期"]=pd.to_datetime(df[dc],errors="coerce"); df["_收盘价"]=df[pc].apply(safe_float)
    df=df.dropna(subset=["_日期","_收盘价"])
    if df.empty: return pd.DataFrame()
    df["年份"]=df["_日期"].dt.year
    out=df.sort_values("_日期").groupby("年份",as_index=False).tail(1).copy()
    return out[["年份","_日期","_收盘价"]].rename(columns={"_日期":"年末日期","_收盘价":"年末收盘价"})

def prepare_eps_data(trend):
    if trend is None or trend.empty: return pd.DataFrame()
    dc=_date_col(trend); ec=_eps_col(trend)
    if dc is None or ec is None: return pd.DataFrame()
    df=trend.copy(); df["_报告日期"]=pd.to_datetime(df[dc],errors="coerce"); df["EPS"]=df[ec].apply(safe_float)
    df=df.dropna(subset=["_报告日期","EPS"])
    if df.empty: return pd.DataFrame()
    df["年份"]=df["_报告日期"].dt.year
    # 每年优先使用12月年报；若没有年报，再使用该年最后一份有效报告。
    df["_年报"]=df["_报告日期"].dt.month.eq(12)
    annual=df[df["_年报"]].sort_values("_报告日期").groupby("年份",as_index=False).tail(1)
    other=df.sort_values("_报告日期").groupby("年份",as_index=False).tail(1)
    out=other[["年份","EPS"]].copy()
    if not annual.empty:
        amap=dict(zip(annual["年份"],annual["EPS"]))
        out["EPS"]=out.apply(lambda r: amap.get(r["年份"],r["EPS"]),axis=1)
    return out

def build_historical_pe(history,trend,max_years=10):
    p=prepare_price_data(history); e=prepare_eps_data(trend)
    if p.empty or e.empty: return pd.DataFrame()
    r=p.merge(e,on="年份",how="inner")
    r=r[r["EPS"]>0].copy()
    if r.empty: return pd.DataFrame()
    r["PE"]=r["年末收盘价"]/r["EPS"]
    r=r.replace([float("inf"),-float("inf")],pd.NA).dropna(subset=["PE"])
    r=r.sort_values("年份").tail(max_years).reset_index(drop=True)
    return r[["年份","年末日期","年末收盘价","EPS","PE"]]

def calculate_historical_statistics(historical_pe,current_pe):
    empty={"min":None,"q25":None,"median":None,"q75":None,"max":None,"percentile":None,"deviation":None}
    if historical_pe is None or historical_pe.empty or "PE" not in historical_pe.columns: return empty
    vals=pd.to_numeric(historical_pe["PE"],errors="coerce").dropna()
    vals=vals[vals>0]
    if vals.empty: return empty
    percentile=None
    if current_pe is not None:
        cp=float(current_pe)
        percentile=float((vals<=cp).sum()/len(vals)*100)
    med=float(vals.median())
    return {"min":float(vals.min()),"q25":float(vals.quantile(.25)),"median":med,"q75":float(vals.quantile(.75)),"max":float(vals.max()),"percentile":percentile,"deviation":None if current_pe is None or med<=0 else float((current_pe/med-1)*100)}

def get_historical_valuation_level(percentile):
    if percentile is None: return "数据不足"
    if percentile<=20: return "历史低位"
    if percentile<=40: return "历史中低位"
    if percentile<=60: return "历史中枢"
    if percentile<=80: return "历史中高位"
    return "历史高位"
