"""A股价值研投｜支付接口 V1

支持后续接入微信支付 Native/JSAPI 或其他支付渠道。
密钥只从环境变量读取，不进入 GitHub。
当前没有真实商户参数时，页面自动显示“待配置”，不产生虚假支付订单。
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Optional


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
            self.mchid
            and self.appid
            and self.api_v3_key
            and self.merchant_serial_no
            and self.private_key
            and self.notify_url
        )


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


def create_order(user_id: str, plan: str = "pro", amount_fen: int = 9900) -> dict:
    """创建支付订单参数草案。

    未配置正式商户参数时不会调用支付平台，也不会伪造成功订单。
    """
    cfg = load_payment_config()
    order_no = "VS" + uuid.uuid4().hex[:24].upper()
    if not cfg.ready:
        return {
            "ok": False,
            "configured": False,
            "order_no": order_no,
            "message": "支付商户参数尚未配置，请先完成微信支付商户号与证书配置。",
        }
    if cfg.provider != "wechat":
        return {
            "ok": False,
            "configured": True,
            "order_no": order_no,
            "message": f"暂未实现 {cfg.provider} 的真实下单适配器。",
        }
    return {
        "ok": False,
        "configured": True,
        "order_no": order_no,
        "user_id": str(user_id),
        "plan": plan,
        "amount_fen": int(amount_fen),
        "notify_url": cfg.notify_url,
        "message": "微信支付参数已配置；下一步接入官方 Native 下单接口与支付回调。",
    }
