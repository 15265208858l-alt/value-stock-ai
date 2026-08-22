"""
ValueStock AI
最终投资决策模块 V16.4 校准版

原则：
1. 综合评分用于衡量总体质量，不单独决定买卖。
2. 估值、风险优先于分数触发硬约束。
3. 数据不足时明确降低置信度，不直接判定公司很差。
4. 允许“优秀公司 + 当前价格一般”进入等待名单，而不是全部归为暂不考虑。
"""


def make_investment_decision(
    investment_score,
    valuation_level,
    historical_level,
    risk_level
):
    try:
        investment_score = float(investment_score)
    except (TypeError, ValueError):
        investment_score = 0

    valuation_level = str(valuation_level or "数据不足")
    historical_level = str(historical_level or "数据不足")
    risk_level = str(risk_level or "数据不足")

    # 最高优先级：真实高风险
    if risk_level == "高风险":
        return {
            "decision": "🔴 原则上回避",
            "action": "暂不买入",
            "position": "0%",
            "reason": "存在较高财务风险，估值便宜也不能抵消核心风险。"
        }

    # 优质 + 低估/合理 + 风险可接受
    if (
        investment_score >= 78
        and valuation_level in [
            "明显低估",
            "较低估值",
            "偏低估值",
            "合理附近"
        ]
        and risk_level in [
            "低风险",
            "风险较低",
            "需要关注",
            "数据不足"
        ]
    ):
        return {
            "decision": "🟢 可以分批建仓",
            "action": "分批买入，控制节奏",
            "position": "10%—25%",
            "reason": "综合质量达到较高水平，估值处于低估或合理区间，当前更适合用分批方式建立仓位。"
        }

    # 公司质量较好，但价格一般
    if (
        investment_score >= 72
        and valuation_level == "合理附近"
        and risk_level not in ["高风险", "风险较高"]
    ):
        return {
            "decision": "🟡 小仓关注",
            "action": "建立观察仓",
            "position": "5%—10%",
            "reason": "公司质量较好，但安全边际尚未特别突出，适合小仓观察而不是一次性重仓。"
        }

    # 优质公司但估值明显偏高：等待，而不是直接否定公司
    if (
        investment_score >= 70
        and valuation_level in [
            "偏高估值",
            "明显偏高",
            "高估"
        ]
    ):
        return {
            "decision": "🟡 等待更好价格",
            "action": "不追高，加入观察名单",
            "position": "0%—5%",
            "reason": "企业质量与长期逻辑未必差，但当前价格缺乏足够安全边际，重点等待估值回落或盈利继续增长。"
        }

    # 中等质量/数据不足：观察，而不是全部判定为失败
    if investment_score >= 60:
        return {
            "decision": "🟠 谨慎观察",
            "action": "继续跟踪基本面",
            "position": "0%—5%",
            "reason": "当前综合优势一般或部分关键数据不足，建议继续观察财务质量、估值和风险变化。"
        }

    return {
        "decision": "🔴 暂不考虑",
        "action": "暂不买入",
        "position": "0%",
        "reason": "当前综合质量或风险收益比尚未达到长期价值投资的优先标准。"
    }
