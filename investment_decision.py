"""
ValueStock AI
最终投资决策模块 V17.0

新增：
- 识别“绝对估值高、但相对同行不贵”的成长股。
- 相对估值只负责调整节奏，不覆盖硬风险与绝对安全边际。
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

    # 1 硬风险优先
    if risk_level == "高风险":
        return {
            "decision": "🔴 原则上回避",
            "action": "暂不买入",
            "position": "0%",
            "reason": "存在较高财务风险，同行相对估值较好也不能抵消核心风险。",
        }

    # 2 绝对高估 + 同行相对便宜：不把它判成“差公司”，但仍不追高
    if (
        investment_score >= 45
        and valuation_level in ["偏高估值", "明显偏高", "高估"]
        and relative_level in ["同行明显便宜", "同行相对便宜", "同行相对合理"]
        and risk_level not in ["高风险"]
    ):
        return {
            "decision": "🟡 高成长高估值，等待",
            "action": "不追高，加入重点观察名单",
            "position": "0%—5%",
            "reason": "公司可能具备较强成长能力，且相对同行估值并不占明显劣势；但绝对估值仍偏高，当前安全边际不足，应等待盈利继续兑现或价格回落。",
        }

    # 3 历史高位 + 当前低估/合理：限制仓位
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

    # 4 高质量 + 当前低估/合理
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

    # 5 公司质量较好 + 合理估值
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

    # 6 优质公司但绝对估值偏高
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

    # 7 中等质量/数据不足
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
