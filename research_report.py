"""A股价值研投｜研究报告 V1
商业层模块：只消费研究快照，不修改核心研究引擎。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


def _fmt(value: Any, digits: int = 2, suffix: str = "") -> str:
    try:
        if value is None or value == "":
            return "暂无"
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "暂无"


def build_research_report(snapshot: Dict[str, Any]) -> str:
    """根据已完成研究快照生成一份可下载的 Markdown 研究报告。"""
    code = str(snapshot.get("code", ""))
    name = str(snapshot.get("name", code) or code)
    score = snapshot.get("score")
    rating = str(snapshot.get("rating", "暂无"))
    decision = str(snapshot.get("decision", "暂无"))
    action = str(snapshot.get("action", "暂无"))
    position = str(snapshot.get("position", "暂无"))
    price = snapshot.get("price")
    normal_value = snapshot.get("normal_value")
    safety_margin = snapshot.get("safety_margin")
    valuation = str(snapshot.get("valuation_level", "数据不足"))
    historical = str(snapshot.get("historical_level", "数据不足"))
    risk = str(snapshot.get("risk_level", "数据不足"))

    if safety_margin is None:
        price_judgement = "当前安全边际暂无，建议结合实时行情再次研究。"
    elif safety_margin >= 20:
        price_judgement = "当前价格相对中性合理价具有较明显安全边际。"
    elif safety_margin >= 0:
        price_judgement = "当前价格接近或略低于中性合理价，安全边际一般。"
    else:
        price_judgement = "当前价格高于中性合理价，安全边际偏弱，宜等待更优价格。"

    risk_note = "当前快照未标记明显高风险。" if "高风险" not in risk and "回避" not in decision else "当前研究结果包含较高风险信号，应优先控制仓位。"

    return f"""# A股价值研投｜个股价值研究报告 V1

**公司：** {name}  
**股票代码：** {code}  
**报告生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  

> 本报告由 A股价值研投基于最近一次完成的核心研究快照生成。报告用于研究辅助，不构成投资建议。

## 一、核心结论

| 项目 | 结果 |
|---|---|
| 综合评分 | {_fmt(score, 0)}/100 |
| 投资评级 | {rating} |
| 最终决策 | {decision} |
| 建议操作 | {action} |
| 建议仓位 | {position} |
| 当前价格 | {_fmt(price)} 元 |
| 中性合理价 | {_fmt(normal_value)} 元 |
| 安全边际 | {_fmt(safety_margin)}% |

**价格判断：** {price_judgement}

## 二、估值结论

**当前估值：** {valuation}  
**历史估值：** {historical}  

研究逻辑重点不是追逐短期涨跌，而是判断企业质量与当前价格是否匹配，并观察是否具备足够安全边际。

## 三、风险结论

**风险等级：** {risk}  
{risk_note}

## 四、跟踪建议

建议后续重点观察：

1. 营收与净利润增长是否延续；
2. 经营现金流与净利润是否持续匹配；
3. 估值是否回落到更有吸引力的价格区间；
4. 核心风险项是否出现恶化；
5. 公司基本面是否仍符合长期价值投资逻辑。

## 五、免责声明

本报告由程序根据已有研究快照自动生成，仅用于信息整理与投资研究辅助，不构成任何证券投资建议、收益承诺或买卖依据。实际投资应结合最新公告、财报、市场环境及个人风险承受能力独立判断。

---

**A股价值研投｜ValueStock AI**  
*用AI研究价值，而不是追逐情绪。*
"""
