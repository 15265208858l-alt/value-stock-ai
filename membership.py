"""A股价值研投｜商业化会员能力层（只负责权限，不参与核心研究计算）

原则：
1. 不修改核心研究引擎。
2. 默认用户为 free，确保未配置会员系统时应用可正常运行。
3. 后续可把这里的身份来源替换为数据库、登录系统或支付回调。
"""

from dataclasses import dataclass
from typing import Iterable, Optional


PLAN_FREE = "free"
PLAN_PRO = "pro"


@dataclass(frozen=True)
class Membership:
    plan: str = PLAN_FREE
    user_id: str = "guest"

    @property
    def is_pro(self) -> bool:
        return self.plan == PLAN_PRO


def normalize_plan(value: Optional[str]) -> str:
    """把外部传入的会员等级安全归一化。"""
    value = (value or "").strip().lower()
    return PLAN_PRO if value == PLAN_PRO else PLAN_FREE


def get_membership(user_id: str = "guest", plan: Optional[str] = None) -> Membership:
    """当前为无登录依赖的轻量实现。

    后续正式商业化时，只需要替换本函数的数据来源，不需要改动核心研究模块。
    """
    return Membership(user_id=user_id or "guest", plan=normalize_plan(plan))


def has_feature(membership: Membership, feature: str) -> bool:
    """统一权限判断入口。"""
    free_features = {
        "basic_research",
        "core_score",
        "core_valuation",
        "risk_check",
    }
    pro_features = free_features | {
        "watchlist",
        "valuation_alert",
        "deep_history",
        "research_report",
        "multi_stock_compare",
    }
    allowed = pro_features if membership.is_pro else free_features
    return feature in allowed


def feature_label(feature: str) -> str:
    labels = {
        "watchlist": "自选股票池",
        "valuation_alert": "估值提醒",
        "deep_history": "深度历史估值",
        "research_report": "专业研究报告",
        "multi_stock_compare": "多股票深度对比",
    }
    return labels.get(feature, feature)


def require_pro(membership: Membership, feature: str) -> dict:
    """返回 UI 层需要的权限状态，不抛异常，不干扰研究流程。"""
    allowed = has_feature(membership, feature)
    return {
        "allowed": allowed,
        "feature": feature,
        "label": feature_label(feature),
        "plan_required": None if allowed else PLAN_PRO,
        "message": "已解锁" if allowed else f"{feature_label(feature)}为专业会员功能",
    }


def plan_catalog() -> Iterable[dict]:
    """前端展示用套餐定义；价格暂不写死，避免过早绑定支付方案。"""
    return [
        {
            "plan": PLAN_FREE,
            "name": "免费研究",
            "positioning": "建立认知，体验核心价值投研框架",
            "features": [
                "单只股票基础研究",
                "企业质量与风险排查",
                "核心估值与投资评分",
            ],
        },
        {
            "plan": PLAN_PRO,
            "name": "专业会员",
            "positioning": "持续跟踪重点股票，提升研究效率",
            "features": [
                "重点股票池",
                "估值/价格提醒",
                "深度历史估值",
                "专业研究报告",
                "多股票深度比较",
            ],
        },
    ]
