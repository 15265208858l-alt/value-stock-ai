"""A股价值研投｜支付接口 V2

当前实现：支付配置检查 + 订单号生成 + 统一订单状态入口。
真实微信 Native 下单仍需使用官方商户接口与证书完成签名请求；密钥只从环境变量读取。
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict


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
        return bool(self.mchid and self.appid and self.api_v3_key and self.merchant_serial_no and self.private_key and self.notify_url)


def load_payment_config() -> PaymentConfig:
    return PaymentConfig(
        provider=os.getenv("VALUESTOCK_PAYMENT_PROVIDER", "wechat").strip().lower() or "wechat",
        mchid=os.getenv("WECHAT_MCHID", "").strip(),
        appid=os.getenv("WECHAT_APPID", "").strip(),
        api_v3_key=os.getenv("WECHAT_API_V3_KEY", "").strip(),
        merchant_serial_no=os.getenv("WECHAT_MERCHANT_SERIAL_NO", "").strip(),
        private_key=os.getenv("WECHAT_PRIVATE_KEY", "").strip(),
        notify_url=os.getenv("WECHAT_NOTIFY_URL", "").strip(),
    )


def make_order_no() -> str:
    return "VS" + uuid.uuid4().hex[:24].upper()


def create_order(user_id: str, plan: str = "pro", amount_fen: int = 9900) -> Dict[str, Any]:
    """返回统一支付订单草案；未完成官方签名请求前绝不伪造支付成功。"""
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
    return {
        "ok": False,
        "configured": True,
        "order_no": order_no,
        "user_id": str(user_id),
        "plan": str(plan),
        "amount_fen": amount_fen,
        "notify_url": cfg.notify_url,
        "message": "支付参数已就绪，待接入微信官方 Native 下单请求。",
    }


def verify_notify_signature(message: str, timestamp: str, nonce: str, signature: str) -> bool:
    """预留回调验签位置；未实现前返回 False，避免误判支付成功。"""
    return bool(message and timestamp and nonce and signature) and False


def build_payment_test_reference(user_id: str, amount_fen: int) -> str:
    """生成本地测试引用，不能作为真实支付成功凭证。"""
    raw = f"{user_id}|{amount_fen}|{time.time_ns()}".encode("utf-8")
    return "TEST_" + hashlib.sha256(raw).hexdigest()[:20].upper()
