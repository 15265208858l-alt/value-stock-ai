"""A股价值研投｜微信支付 Native V3

正式支付链路：Native 下单 -> code_url -> 主动查询订单 -> 支付成功后开通会员。
敏感参数只从环境变量读取。当前采用主动查询方案，避免在 Streamlit 单进程中伪造或依赖不存在的回调服务。
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Dict

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from user_store import get_payment_order, save_payment_order, mark_payment_paid, extend_pro_membership

WECHAT_HOST = "https://api.mch.weixin.qq.com"
NATIVE_PATH = "/v3/pay/transactions/native"


@dataclass(frozen=True)
class PaymentConfig:
    provider: str = "wechat"
    mchid: str = ""
    appid: str = ""
    api_v3_key: str = ""
    merchant_serial_no: str = ""
    private_key: str = ""
    notify_url: str = ""

    @property
    def ready(self) -> bool:
        return bool(
            self.provider == "wechat"
            and self.mchid
            and self.appid
            and self.api_v3_key
            and self.merchant_serial_no
            and self.private_key
            and self.notify_url
        )


def _env(name: str) -> str:
    return os.getenv(name, "").replace("\\n", "\n").strip()


def load_payment_config() -> PaymentConfig:
    return PaymentConfig(
        provider=os.getenv("VALUESTOCK_PAYMENT_PROVIDER", "wechat").strip().lower() or "wechat",
        mchid=_env("WECHAT_MCHID"),
        appid=_env("WECHAT_APPID"),
        api_v3_key=_env("WECHAT_API_V3_KEY"),
        merchant_serial_no=_env("WECHAT_MERCHANT_SERIAL_NO"),
        private_key=_env("WECHAT_PRIVATE_KEY"),
        notify_url=_env("WECHAT_NOTIFY_URL"),
    )


def make_order_no() -> str:
    return "VS" + uuid.uuid4().hex[:24].upper()


def _sign_message(cfg: PaymentConfig, method: str, path: str, body: str, nonce: str, timestamp: str) -> str:
    message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}\n"
    key = serialization.load_pem_private_key(cfg.private_key.encode("utf-8"), password=None)
    signature = key.sign(message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    auth_signature = base64.b64encode(signature).decode("ascii")
    return (
        "WECHATPAY2-SHA256-RSA2048 "
        f'mchid="{cfg.mchid}",nonce_str="{nonce}",timestamp="{timestamp}",'
        f'serial_no="{cfg.merchant_serial_no}",signature="{auth_signature}"'
    )


def _request(cfg: PaymentConfig, method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    body = "" if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    nonce = uuid.uuid4().hex
    timestamp = str(int(time.time()))
    headers = {
        "Authorization": _sign_message(cfg, method, path, body, nonce, timestamp),
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ValueStockAI/1.0",
    }
    request = urllib.request.Request(
        WECHAT_HOST + path,
        data=body.encode("utf-8") if method != "GET" else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            raw = response.read().decode("utf-8")
            return {"http_status": response.status, **(json.loads(raw) if raw else {})}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = {"raw": raw}
        return {"http_status": exc.code, "error": True, **detail}
    except Exception as exc:
        return {"http_status": 0, "error": True, "message": f"微信支付请求失败：{type(exc).__name__}: {exc}"}


def create_order(user_id: str, plan: str = "pro", amount_fen: int = 9900) -> Dict[str, Any]:
    cfg = load_payment_config()
    order_no = make_order_no()
    try:
        amount_fen = int(amount_fen)
    except (TypeError, ValueError):
        amount_fen = 0
    if amount_fen <= 0:
        return {"ok": False, "configured": cfg.ready, "order_no": order_no, "message": "支付金额必须大于0。"}
    if not user_id:
        return {"ok": False, "configured": cfg.ready, "order_no": order_no, "message": "请先登录账号。"}
    if not cfg.ready:
        return {"ok": False, "configured": False, "order_no": order_no, "message": "微信支付尚未配置。"}

    payload = {
        "appid": cfg.appid,
        "mchid": cfg.mchid,
        "description": "A股价值研投专业会员",
        "out_trade_no": order_no,
        "notify_url": cfg.notify_url,
        "amount": {"total": amount_fen, "currency": "CNY"},
    }
    result = _request(cfg, "POST", NATIVE_PATH, payload)
    ok = result.get("http_status") == 200 and bool(result.get("code_url"))
    save_payment_order(
        order_no=order_no,
        user_id=str(user_id),
        plan=str(plan),
        amount_fen=amount_fen,
        status="pending" if ok else "failed",
        code_url=result.get("code_url"),
        prepay_id=result.get("prepay_id"),
        raw_response=result,
    )
    if not ok:
        return {"ok": False, "configured": True, "order_no": order_no, "message": result.get("message") or result.get("code") or "微信下单失败。", "detail": result}
    return {
        "ok": True,
        "configured": True,
        "order_no": order_no,
        "user_id": str(user_id),
        "plan": str(plan),
        "amount_fen": amount_fen,
        "code_url": result.get("code_url"),
        "prepay_id": result.get("prepay_id"),
        "message": "微信 Native 订单创建成功，请扫码完成支付。",
    }


def query_order(order_no: str, auto_activate: bool = True) -> Dict[str, Any]:
    cfg = load_payment_config()
    order = get_payment_order(order_no)
    if not order_no or not order:
        return {"ok": False, "paid": False, "message": "订单不存在。"}
    if not cfg.ready:
        return {"ok": False, "paid": False, "message": "微信支付尚未配置。"}
    safe_no = str(order_no).strip()
    path = f"/v3/pay/transactions/out-trade-no/{safe_no}?mchid={cfg.mchid}"
    result = _request(cfg, "GET", path)
    if result.get("http_status") != 200:
        return {"ok": False, "paid": False, "order_no": safe_no, "message": result.get("message") or "订单查询失败。", "detail": result}

    state = str(result.get("trade_state", "")).upper()
    if state == "SUCCESS":
        if auto_activate and order.get("status") != "paid":
            mark_payment_paid(safe_no, result)
            extend_pro_membership(order["user_id"], days=30)
        return {"ok": True, "paid": True, "order_no": safe_no, "trade_state": state, "transaction_id": result.get("transaction_id"), "message": "支付成功，专业会员已开通/续期30天。"}

    return {"ok": True, "paid": False, "order_no": safe_no, "trade_state": state or "UNKNOWN", "message": _trade_state_message(state)}


def _trade_state_message(state: str) -> str:
    return {
        "NOTPAY": "订单尚未支付。",
        "USERPAYING": "用户正在支付，请稍候。",
        "CLOSED": "订单已关闭。",
        "REVOKED": "订单已撤销。",
        "PAYERROR": "支付失败，请重新下单。",
    }.get(state, "订单尚未确认支付成功。")


def verify_notify_signature(message: str, timestamp: str, nonce: str, signature: str) -> bool:
    """回调暂不作为会员开通依据；主动查询官方订单状态更适合当前 Streamlit 单进程架构。"""
    return False


def build_payment_test_reference(user_id: str, amount_fen: int) -> str:
    raw = f"{user_id}|{amount_fen}|{time.time_ns()}".encode("utf-8")
    return "TEST_" + hashlib.sha256(raw).hexdigest()[:20].upper()
