"""A股价值研投｜股票池轻量行情层 V1

独立于核心研究引擎：只负责股票池的最新行情刷新，不重新抓取财务三表。
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import Any, Dict, Iterable

import akshare as ak
import pandas as pd

_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}
TTL = 60
TIMEOUT = 8


def _market_prefix(code: str) -> str:
    return "sh" if code.startswith(("6", "68")) else "sz" if code.startswith(("0", "3")) else "bj"


def _history_quote(code: str) -> Dict[str, Any]:
    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date="20200101",
            end_date="20500101",
            adjust="",
        )
        if df is None or df.empty:
            df = ak.stock_zh_a_hist_tx(
                symbol=_market_prefix(code) + code,
                start_date="20200101",
                end_date="20500101",
                adjust="",
            )
        if df is None or df.empty:
            return {"code": code, "price": None, "change": None, "updated": time.time()}

        close_col = "收盘" if "收盘" in df.columns else "close"
        price = float(df.iloc[-1][close_col])
        change = None
        if len(df) >= 2:
            prev = float(df.iloc[-2][close_col])
            if prev:
                change = (price / prev - 1) * 100
        return {"code": code, "price": price, "change": change, "updated": time.time()}
    except Exception:
        return {"code": code, "price": None, "change": None, "updated": time.time()}


def get_quote(code: str, force: bool = False) -> Dict[str, Any]:
    code = str(code or "").strip()
    if len(code) != 6 or not code.isdigit():
        return {"code": code, "price": None, "change": None, "updated": time.time()}
    now = time.time()
    cached = _CACHE.get(code)
    if cached and not force and now - cached[0] < TTL:
        return cached[1]
    result = _history_quote(code)
    _CACHE[code] = (now, result)
    return result


def get_quotes(codes: Iterable[str], force: bool = False) -> Dict[str, Dict[str, Any]]:
    clean = sorted({str(c).strip() for c in codes if str(c).strip().isdigit() and len(str(c).strip()) == 6})
    if not clean:
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    pending = []
    now = time.time()
    for code in clean:
        cached = _CACHE.get(code)
        if cached and not force and now - cached[0] < TTL:
            out[code] = cached[1]
        else:
            pending.append(code)

    if pending:
        with ThreadPoolExecutor(max_workers=min(5, len(pending))) as ex:
            futures = {ex.submit(get_quote, code, True): code for code in pending}
            for future in as_completed(futures, timeout=TIMEOUT):
                code = futures[future]
                try:
                    out[code] = future.result()
                except Exception:
                    out[code] = {"code": code, "price": None, "change": None, "updated": time.time()}
    for code in clean:
        out.setdefault(code, {"code": code, "price": None, "change": None, "updated": time.time()})
    return out
