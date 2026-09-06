"""A股价值研投｜用户、会员、研究与股票池数据层 V4"""
from __future__ import annotations
import hashlib,json,os,sqlite3
from datetime import datetime,timedelta,timezone
from typing import Any,Dict,Optional
DB_PATH=os.getenv("VALUESTOCK_DB_PATH","valuestock.db")
def _connect():
    c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row; return c
def init_db():
    with _connect() as c:c.executescript('''CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,display_name TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS memberships(user_id TEXT PRIMARY KEY,plan TEXT NOT NULL DEFAULT 'free',status TEXT NOT NULL DEFAULT 'active',expires_at TEXT,updated_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(user_id));CREATE TABLE IF NOT EXISTS research_history(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT NOT NULL,code TEXT NOT NULL,name TEXT,score REAL,decision TEXT,price REAL,normal_value REAL,safety_margin REAL,created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(user_id));CREATE INDEX IF NOT EXISTS idx_research_user_time ON research_history(user_id,created_at DESC);CREATE TABLE IF NOT EXISTS watchlist(user_id TEXT NOT NULL,code TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(user_id,code),FOREIGN KEY(user_id) REFERENCES users(user_id));CREATE INDEX IF NOT EXISTS idx_watchlist_user_time ON watchlist(user_id,updated_at DESC);CREATE TABLE IF NOT EXISTS payment_orders(order_no TEXT PRIMARY KEY,user_id TEXT NOT NULL,plan TEXT NOT NULL,amount_fen INTEGER NOT NULL,status TEXT NOT NULL,code_url TEXT,prepay_id TEXT,transaction_id TEXT,raw_response TEXT,created_at TEXT NOT NULL,paid_at TEXT,FOREIGN KEY(user_id) REFERENCES users(user_id));CREATE INDEX IF NOT EXISTS idx_payment_user_time ON payment_orders(user_id,created_at DESC);''')
def make_user_id(email):return 'u_'+hashlib.sha256(str(email or '').strip().lower().encode()).hexdigest()[:24]
def upsert_user(email,display_name=''):
    init_db();email=str(email or '').strip().lower();uid=make_user_id(email);name=str(display_name or email.split('@')[0]).strip() or email.split('@')[0];now=datetime.now(timezone.utc).isoformat()
    with _connect() as c:
        c.execute('INSERT INTO users(user_id,email,display_name,created_at,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(email) DO UPDATE SET display_name=excluded.display_name,updated_at=excluded.updated_at',(uid,email,name,now,now));c.execute('INSERT INTO memberships(user_id,plan,status,expires_at,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO NOTHING',(uid,'free','active',None,now));r=c.execute('SELECT user_id,email,display_name,created_at,updated_at FROM users WHERE email=?',(email,)).fetchone();return dict(r)
def get_membership(uid):
    init_db();
    with _connect() as c:r=c.execute('SELECT user_id,plan,status,expires_at,updated_at FROM memberships WHERE user_id=?',(str(uid),)).fetchone()
    return dict(r) if r else {'user_id':str(uid),'plan':'free','status':'active','expires_at':None}
def set_membership(uid,plan,status='active',expires_at=None):
    init_db();now=datetime.now(timezone.utc).isoformat();plan='pro' if str(plan).lower()=='pro' else 'free'
    with _connect() as c:c.execute('INSERT INTO memberships(user_id,plan,status,expires_at,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan,status=excluded.status,expires_at=excluded.expires_at,updated_at=excluded.updated_at',(str(uid),plan,status,expires_at,now))
def extend_pro_membership(uid,days=30):
    now=datetime.now(timezone.utc);m=get_membership(uid);base=now
    try:base=max(now,datetime.fromisoformat(str(m.get('expires_at')).replace('Z','+00:00'))) if m.get('expires_at') else now
    except ValueError:pass
    exp=(base+timedelta(days=max(1,int(days)))).isoformat();set_membership(uid,'pro','active',exp);return exp
def save_research_snapshot(uid,s):
    if not uid:return
    init_db();now=datetime.now(timezone.utc).isoformat()
    with _connect() as c:c.execute('INSERT INTO research_history(user_id,code,name,score,decision,price,normal_value,safety_margin,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(str(uid),str(s.get('code','')),str(s.get('name','')),s.get('score'),str(s.get('decision','')),s.get('price'),s.get('normal_value'),s.get('safety_margin'),now))
def recent_research(uid,limit=10):
    init_db();limit=max(1,min(int(limit),50))
    with _connect() as c:r=c.execute('SELECT code,name,score,decision,price,normal_value,safety_margin,created_at FROM research_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?',(str(uid),limit)).fetchall()
    return [dict(x) for x in r]
def latest_research_for_codes(uid,codes):
    """返回每只股票最近一次研究结果，用于股票池快速恢复，不重新跑核心研究。"""
    init_db(); codes=[str(x) for x in (codes or []) if str(x)]
    if not uid or not codes:return {}
    marks=','.join('?'*len(codes)); params=[str(uid),*codes]
    with _connect() as c:r=c.execute(f'''SELECT code,name,score,decision,price,normal_value,safety_margin,created_at FROM research_history WHERE user_id=? AND code IN ({marks}) ORDER BY created_at DESC''',params).fetchall()
    out={}
    for x in r:
        d=dict(x);out.setdefault(str(d['code']),d)
    return out
def get_watchlist(uid,limit=20):
    if not uid:return []
    init_db();limit=max(1,min(int(limit),100))
    with _connect() as c:r=c.execute('SELECT code FROM watchlist WHERE user_id=? ORDER BY updated_at DESC LIMIT ?',(str(uid),limit)).fetchall()
    return [str(x['code']) for x in r]
def add_watchlist_stock(uid,code,max_stocks=20):
    if not uid or not code:return False
    init_db();code=str(code).strip();now=datetime.now(timezone.utc).isoformat()
    with _connect() as c:
        if c.execute('SELECT 1 FROM watchlist WHERE user_id=? AND code=?',(str(uid),code)).fetchone():c.execute('UPDATE watchlist SET updated_at=? WHERE user_id=? AND code=?',(now,str(uid),code));return True
        if int(c.execute('SELECT COUNT(*) n FROM watchlist WHERE user_id=?',(str(uid),)).fetchone()['n'])>=int(max_stocks):return False
        c.execute('INSERT INTO watchlist(user_id,code,created_at,updated_at) VALUES(?,?,?,?)',(str(uid),code,now,now))
    return True
def remove_watchlist_stock(uid,code):
    if not uid or not code:return
    init_db()
    with _connect() as c:c.execute('DELETE FROM watchlist WHERE user_id=? AND code=?',(str(uid),str(code).strip()))
def clear_watchlist(uid):
    if not uid:return
    init_db()
    with _connect() as c:c.execute('DELETE FROM watchlist WHERE user_id=?',(str(uid),))
def save_payment_order(order_no,user_id,plan,amount_fen,status,code_url=None,prepay_id=None,raw_response=None):
    init_db();now=datetime.now(timezone.utc).isoformat()
    with _connect() as c:c.execute('INSERT INTO payment_orders(order_no,user_id,plan,amount_fen,status,code_url,prepay_id,raw_response,created_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(order_no) DO UPDATE SET status=excluded.status,code_url=excluded.code_url,prepay_id=excluded.prepay_id,raw_response=excluded.raw_response',(str(order_no),str(user_id),str(plan),int(amount_fen),str(status),code_url,prepay_id,json.dumps(raw_response or {},ensure_ascii=False),now))
def get_payment_order(order_no):
    init_db()
    with _connect() as c:r=c.execute('SELECT * FROM payment_orders WHERE order_no=?',(str(order_no),)).fetchone()
    return dict(r) if r else None
def mark_payment_paid(order_no,provider_response=None):
    init_db();now=datetime.now(timezone.utc).isoformat();x=provider_response or {}
    with _connect() as c:c.execute("UPDATE payment_orders SET status='paid',transaction_id=?,raw_response=?,paid_at=? WHERE order_no=?",(x.get('transaction_id'),json.dumps(x,ensure_ascii=False),now,str(order_no)))
