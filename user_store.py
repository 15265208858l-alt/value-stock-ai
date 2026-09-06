"""A股价值研投｜用户、会员、研究与股票池数据层 V4"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

DB_PATH = os.getenv("VALUESTOCK_DB_PATH", "valuestock.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memberships (
            user_id TEXT PRIMARY KEY, plan TEXT NOT NULL DEFAULT 'free', status TEXT NOT NULL DEFAULT 'active',
            expires_at TEXT, updated_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS research_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, code TEXT NOT NULL, name TEXT,
            score REAL, decision TEXT, price REAL, normal_value REAL, safety_margin REAL, created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_research_user_time ON research_history(user_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS watchlist (
            user_id TEXT NOT NULL, code TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            PRIMARY KEY(user_id, code), FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_watchlist_user_time ON watchlist(user_id, updated_at DESC);
        CREATE TABLE IF NOT EXISTS payment_orders (
            order_no TEXT PRIMARY KEY, user_id TEXT NOT NULL, plan TEXT NOT NULL, amount_fen INTEGER NOT NULL,
            status TEXT NOT NULL, code_url TEXT, prepay_id TEXT, transaction_id TEXT, raw_response TEXT,
            created_at TEXT NOT NULL, paid_at TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_payment_user_time ON payment_orders(user_id, created_at DESC);
        """)


def make_user_id(email: str) -> str:
    return "u_" + hashlib.sha256(str(email or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def upsert_user(email: str, display_name: str = "") -> Dict[str, Any]:
    init_db(); email = str(email or "").strip().lower(); user_id = make_user_id(email)
    name = str(display_name or email.split("@")[0]).strip() or email.split("@")[0]
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("""INSERT INTO users(user_id,email,display_name,created_at,updated_at) VALUES(?,?,?,?,?)
        ON CONFLICT(email) DO UPDATE SET display_name=excluded.display_name,updated_at=excluded.updated_at""", (user_id,email,name,now,now))
        conn.execute("""INSERT INTO memberships(user_id,plan,status,expires_at,updated_at) VALUES(?,?,?,?,?)
        ON CONFLICT(user_id) DO NOTHING""", (user_id,"free","active",None,now))
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return dict(row) if row else {"user_id":user_id,"email":email,"display_name":name}


def get_membership(user_id: str) -> Dict[str, Any]:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM memberships WHERE user_id=?", (str(user_id),)).fetchone()
    return dict(row) if row else {"user_id":str(user_id),"plan":"free","status":"active","expires_at":None}


def set_membership(user_id: str, plan: str, status: str = "active", expires_at: Optional[str] = None) -> None:
    init_db(); plan = "pro" if str(plan).strip().lower()=="pro" else "free"; now=datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("""INSERT INTO memberships(user_id,plan,status,expires_at,updated_at) VALUES(?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan,status=excluded.status,expires_at=excluded.expires_at,updated_at=excluded.updated_at""",
        (str(user_id),plan,str(status or "active"),expires_at,now))


def extend_pro_membership(user_id: str, days: int = 30) -> str:
    now=datetime.now(timezone.utc); current=get_membership(user_id); base=now
    if current.get("expires_at"):
        try: base=max(now,datetime.fromisoformat(str(current["expires_at"]).replace("Z","+00:00")))
        except ValueError: pass
    expires=(base+timedelta(days=max(1,int(days)))).isoformat(); set_membership(user_id,"pro","active",expires); return expires


def save_research_snapshot(user_id: str, snapshot: Dict[str, Any]) -> None:
    if not user_id: return
    init_db(); now=datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("""INSERT INTO research_history(user_id,code,name,score,decision,price,normal_value,safety_margin,created_at)
        VALUES(?,?,?,?,?,?,?,?,?)""", (str(user_id),str(snapshot.get("code","")),str(snapshot.get("name","")),snapshot.get("score"),str(snapshot.get("decision","")),snapshot.get("price"),snapshot.get("normal_value"),snapshot.get("safety_margin"),now))


def recent_research(user_id: str, limit: int = 10):
    init_db(); safe_limit=max(1,min(int(limit),50))
    with _connect() as conn:
        rows=conn.execute("SELECT code,name,score,decision,price,normal_value,safety_margin,created_at FROM research_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",(str(user_id),safe_limit)).fetchall()
    return [dict(r) for r in rows]


def latest_research_for_codes(user_id: str, codes) -> Dict[str, Dict[str, Any]]:
    """每只股票只取该账号最近一次研究结果，用于股票池快速展示。"""
    if not user_id: return {}
    codes=[str(c).strip() for c in (codes or []) if str(c).strip()]
    if not codes: return {}
    init_db(); placeholders=",".join("?"*len(codes)); params=[str(user_id),*codes]
    with _connect() as conn:
        rows=conn.execute(f"""SELECT code,name,score,decision,price,normal_value,safety_margin,created_at
        FROM research_history WHERE user_id=? AND code IN ({placeholders}) ORDER BY created_at DESC""",params).fetchall()
    out={}
    for row in rows:
        d=dict(row); out.setdefault(str(d["code"]),d)
    return out


def get_watchlist(user_id: str, limit: int = 20):
    if not user_id: return []
    init_db(); safe_limit=max(1,min(int(limit),100))
    with _connect() as conn:
        rows=conn.execute("SELECT code FROM watchlist WHERE user_id=? ORDER BY updated_at DESC LIMIT ?",(str(user_id),safe_limit)).fetchall()
    return [str(r["code"]) for r in rows]


def add_watchlist_stock(user_id: str, code: str, max_stocks: int = 20) -> bool:
    if not user_id or not code: return False
    init_db(); code=str(code).strip(); now=datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        if conn.execute("SELECT 1 FROM watchlist WHERE user_id=? AND code=?",(str(user_id),code)).fetchone():
            conn.execute("UPDATE watchlist SET updated_at=? WHERE user_id=? AND code=?",(now,str(user_id),code)); return True
        n=conn.execute("SELECT COUNT(*) n FROM watchlist WHERE user_id=?",(str(user_id),)).fetchone()["n"]
        if int(n)>=int(max_stocks): return False
        conn.execute("INSERT INTO watchlist(user_id,code,created_at,updated_at) VALUES(?,?,?,?)",(str(user_id),code,now,now))
    return True


def remove_watchlist_stock(user_id: str, code: str) -> None:
    if not user_id or not code: return
    init_db()
    with _connect() as conn: conn.execute("DELETE FROM watchlist WHERE user_id=? AND code=?",(str(user_id),str(code).strip()))


def clear_watchlist(user_id: str) -> None:
    if not user_id: return
    init_db()
    with _connect() as conn: conn.execute("DELETE FROM watchlist WHERE user_id=?",(str(user_id),))


def save_payment_order(order_no: str, user_id: str, plan: str, amount_fen: int, status: str, code_url: Optional[str]=None, prepay_id: Optional[str]=None, raw_response: Optional[Dict[str,Any]]=None) -> None:
    init_db(); now=datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("""INSERT INTO payment_orders(order_no,user_id,plan,amount_fen,status,code_url,prepay_id,raw_response,created_at)
        VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(order_no) DO UPDATE SET status=excluded.status,code_url=excluded.code_url,prepay_id=excluded.prepay_id,raw_response=excluded.raw_response""",
        (str(order_no),str(user_id),str(plan),int(amount_fen),str(status),code_url,prepay_id,json.dumps(raw_response or {},ensure_ascii=False),now))


def get_payment_order(order_no: str) -> Optional[Dict[str,Any]]:
    init_db()
    with _connect() as conn: row=conn.execute("SELECT * FROM payment_orders WHERE order_no=?",(str(order_no),)).fetchone()
    return dict(row) if row else None


def mark_payment_paid(order_no: str, provider_response: Optional[Dict[str,Any]]=None) -> None:
    init_db(); now=datetime.now(timezone.utc).isoformat(); response=provider_response or {}
    with _connect() as conn: conn.execute("UPDATE payment_orders SET status='paid',transaction_id=?,raw_response=?,paid_at=? WHERE order_no=?",(response.get("transaction_id"),json.dumps(response,ensure_ascii=False),now,str(order_no)))
