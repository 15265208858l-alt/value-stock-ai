"""
ValueStock AI
最终投资决策模块 V17.0.2

校准：
- 高估但相对同行合理/略贵/便宜的成长股，优先给出“等待/观察”，而不是直接“暂不考虑”。
- 只有同行明显偏贵、绝对高估、风险较高等组合，才继续维持更严格结论。
- 硬风险最高优先级。
"""

from peer_compare import get_last_relative_valuation


def make_investment_decision(
    investment_score,
    valuation_level,
    historical_level,
    risk_level,
):
    try:
        investment_score = float(investment_score)
    except (TypeError, ValueError):
        investment_score = 0.0

    valuation_level = str(valuation_level or "数据不足")
    historical_level = str(historical_level or "数据不足")
    risk_level = str(risk_level or "数据不足")

    relative = get_last_relative_valuation()
    relative_level = relative.get("level", "数据不足")

    if risk_level == "高风险":
        return {
            "decision": "🔴 原则上回避",
            "action": "暂不买入",
            "position": "0%",
            "reason": "存在较高财务风险，同行相对估值不能抵消核心风险。",
        }

    # 高估 + 同行明显便宜/相对合理/仅略贵：进入等待或重点观察。
    # 对于“同行相对偏贵”，要求更高一点的评分，避免把明显弱势公司放宽过头。
    if (
        investment_score >= 50
        and valuation_level in ["偏高估值", "明显偏高", "高估"]
        and relative_level in ["同行明显便宜", "同行相对便宜", "同行相对合理"]
        and risk_level not in ["高风险", "风险较高"]
    ):
        return {
            "decision": "🟡 高成长高估值，等待",
            "action": "不追高，加入重点观察名单",
            "position": "0%—5%",
            "reason": "绝对估值偏高，但相对同行并不明显昂贵；当前更适合等待盈利继续兑现或价格回落。",
        }

    if (
        investment_score >= 50
        and valuation_level in ["偏高估值", "明显偏高", "高估"]
        and relative_level == "同行相对偏贵"
        and risk_level not in ["高风险", "风险较高"]
    ):
        return {
            "decision": "🟠 谨慎观察，等待更好价格",
            "action": "不追高，继续跟踪",
            "position": "0%—3%",
            "reason": "公司仍可能具备较强成长能力，但绝对估值偏高且相对同行也略贵，当前安全边际不足，因此先观察，不追高。",
        }

    if (
        investment_score >= 75
        and historical_level == "历史高位"
        and valuation_level in ["明显低估", "较低估值", "偏低估值", "合理附近"]
        and risk_level not in ["高风险", "风险较高"]
    ):
        return {
            "decision": "🟡 小仓关注",
            "action": "先小仓试探，等待历史估值回落",
            "position": "5%—10%",
            "reason": "当前模型显示价格并不昂贵，但历史估值处于高位，建议控制建仓节奏。",
        }

    if (
        investment_score >= 78
        and valuation_level in ["明显低估", "较低估值", "偏低估值", "合理附近"]
        and historical_level != "历史高位"
        and risk_level in ["低风险", "风险较低", "需要关注", "数据不足"]
    ):
        return {
            "decision": "🟢 可以分批建仓",
            "action": "分批买入，控制节奏",
            "position": "10%—25%",
            "reason": "综合质量较高，当前估值处于低估或合理区间，具备一定安全边际。",
        }

    if (
        investment_score >= 72
        and valuation_level == "合理附近"
        and historical_level != "历史高位"
        and risk_level not in ["高风险", "风险较高"]
    ):
        return {
            "decision": "🟡 小仓关注",
            "action": "建立观察仓",
            "position": "5%—10%",
            "reason": "公司质量较好，但安全边际尚未特别突出。",
        }

    if (
        investment_score >= 65
        and valuation_level in ["偏高估值", "明显偏高", "高估"]
    ):
        return {
            "decision": "🟡 等待更好价格",
            "action": "不追高，加入观察名单",
            "position": "0%—5%",
            "reason": "企业质量与长期逻辑未必差，但绝对价格缺乏足够安全边际。",
        }

    if investment_score >= 60:
        return {
            "decision": "🟠 谨慎观察",
            "action": "继续跟踪基本面",
            "position": "0%—5%",
            "reason": "当前综合优势一般或部分关键数据不足。",
        }

    return {
        "decision": "🔴 暂不考虑",
        "action": "暂不买入",
        "position": "0%",
        "reason": "当前综合质量或风险收益比尚未达到长期价值投资的优先标准。",
    }
