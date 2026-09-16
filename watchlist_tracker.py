"""A股价值研投｜股票池轻量行情跟踪 V1

商业层独立模块：只请求股票池中的最新行情，不重新跑完整财务研究。
行情失败时保留最近一次研究快照，不影响核心研究链路。
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List


def _clean(code: Any) -> str:
    value = re.sub(r"\D", "", str(code or ""))
    return value if len(value) == 6 else ""


def _market_code(code: str) -> str:
    return ("sh" if code.startswith(("6", "68")) else "sz" if code.startswith(("0", "3")) else "bj") + code


def _parse_line(line: str) -> Dict[str, Any] | None:
    if '="' not in line:
        return None
    key, raw = line.split('="', 1)
    code = key.rsplit("_", 1)[-1]
    body = raw.rstrip('";')
    parts = body.split("~")
    if len(parts) < 6:
        return None
    try:
        price = float(parts[3]) if parts[3] else None
    except (TypeError, ValueError):
        price = None
    try:
        prev_close = float(parts[4]) if parts[4] else None
    except (TypeError, ValueError):
        prev_close = None
    change = None
    if price is not None and prev_close not in (None, 0):
        change = (price / prev_close - 1) * 100
    return {"code": code, "name": parts[1] or code, "price": price, "change": change}


def load_latest_quotes(codes: Iterable[str], timeout: float = 8.0) -> Dict[str, Dict[str, Any]]:
    clean_codes = [_clean(x) for x in codes]
    clean_codes = list(dict.fromkeys(x for x in clean_codes if x))
    if not clean_codes:
        return {}
    symbols = ",".join(_market_code(code) for code in clean_codes)
    url = "https://qt.gtimg.cn/q=" + urllib.parse.quote(symbols, safe=",")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("gbk", errors="ignore")
    except Exception:
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    for line in text.splitlines():
        item = _parse_line(line)
        if item and item.get("code"):
            result[item["code"]] = item
    return result


def merge_watchlist_quotes(codes: List[str], snapshots: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """合并最新行情与最近研究快照；任何一侧缺失都不制造虚假数据。"""
    quotes = load_latest_quotes(codes)
    rows: List[Dict[str, Any]] = []
    for code in codes:
        snap = snapshots.get(code, {}) or {}
        quote = quotes.get(code, {}) or {}
        price = quote.get("price") if quote.get("price") is not None else snap.get("price")
        change = quote.get("change")
        normal = snap.get("normal_value")
        margin = None
        try:
            if price is not None and normal not in (None, 0):
                margin = (float(normal) / float(price) - 1) * 100
        except (TypeError, ValueError, ZeroDivisionError):
            margin = None
        rows.append({
            "code": code,
            "name": quote.get("name") or snap.get("name") or code,
            "price": price,
            "change": change,
            "normal_value": normal,
            "safety_margin": margin if margin is not None else snap.get("safety_margin"),
            "score": snap.get("score"),
            "rating": snap.get("rating", "未研究"),
            "decision": snap.get("decision", "未研究"),
            "valuation_level": snap.get("valuation_level", "未研究"),
            "historical_level": snap.get("historical_level", "未研究"),
            "risk_level": snap.get("risk_level", "未研究"),
            "quote_live": quote.get("price") is not None,
        })
    return rows
