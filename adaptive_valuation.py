"""
ValueStock AI
行业自适应估值引擎 V16.6.1

核心升级：
1. 普通公司、银行、保险、券商、周期股继续使用差异化估值。
2. 新增并强化“成长科技”模型，避免用成熟制造业的低PE参数系统性压低科技成长股估值。
3. 科技模型采用“成长溢价版 PE + PB”作为第一阶段模型。
4. 自动识别增加科创板（688）科技成长代码兜底，并扩充重点科技股代码库。
5. 数据不足时自动回退，不让估值模块导致程序中断。
"""


def _contains(text, keywords):
    text = str(text or "")
    return any(keyword in text for keyword in keywords)


def detect_valuation_model(industry=None, market_industry=None, stock_code=None, override="自动识别"):
    """返回估值模型类别。优先手动覆盖，其次行业文本，最后做代码兜底。"""

    override_map = {
        "普通成长/制造": "general",
        "银行": "bank",
        "保险": "insurance",
        "券商": "broker",
        "周期": "cyclical",
        "成长科技": "growth_tech",
    }

    if override in override_map:
        return override_map[override]

    text = f"{industry or ''} {market_industry or ''}"

    # 科技成长优先于普通制造识别
    if _contains(text, [
        "半导体", "芯片", "电子", "光通信", "通信设备", "通信服务",
        "AI", "人工智能", "算力", "机器人", "软件", "计算机",
        "云计算", "数据中心", "自动化", "消费电子", "信息技术",
        "元器件", "集成电路", "IT", "互联网", "数字经济"
    ]):
        return "growth_tech"

    if _contains(text, ["保险", "寿险", "财险", "健康险"]):
        return "insurance"

    if _contains(text, ["银行", "商业银行"]):
        return "bank"

    if _contains(text, ["证券", "券商"]):
        return "broker"

    if _contains(text, [
        "煤炭", "钢铁", "有色", "石油", "石化", "化工",
        "铝", "铜", "黄金", "稀土", "水泥"
    ]):
        return "cyclical"

    code = str(stock_code or "").strip()

    insurance_codes = {"601318", "601336", "601601", "000627", "000628"}
    bank_codes = {
        "000001", "002142", "002807", "600000", "600015", "600016", "600036",
        "600919", "601009", "601128", "601166", "601169", "601229", "601288",
        "601328", "601398", "601658", "601818", "601939", "601988", "601997", "601998"
    }
    broker_codes = {
        "000166", "000686", "000728", "000750", "000776", "002500", "600030",
        "600061", "600109", "600837", "601066", "601099", "601211", "601377",
        "601555", "601688", "601878", "601881", "601901", "601995"
    }

    # 重点科技成长代码：半导体 / 光通信 / AI算力 / 软件 / 机器人
    growth_tech_codes = {
        # 光通信 / 通信 / 算力
        "300308", "300502", "300394", "000938", "000977", "601138", "688041", "603019",
        "603516", "600845", "600570", "600588", "600728",
        # 半导体 / 芯片
        "688981", "688256", "688008", "688126", "002371", "002156", "688036",
        "600584", "600460", "603986", "688099", "688012", "688019", "688498",
        # 软件 / AI应用
        "688111", "002230", "300454", "300496", "300674", "300017", "002153",
        # 机器人 / 自动化
        "300124", "688017", "002747", "002472", "300024", "601127"
    }

    if code in insurance_codes:
        return "insurance"
    if code in bank_codes:
        return "bank"
    if code in broker_codes:
        return "broker"
    if code in growth_tech_codes:
        return "growth_tech"

    # 科创板整体以科技成长为主，作为数据接口行业字段缺失时的兜底。
    # 对少数明显属于非科技行业的688公司，后续可加入反向覆盖清单。
    if code.startswith("688"):
        return "growth_tech"

    return "general"


def get_valuation_config(model, annual_roe=None):
    """返回模型参数，供 calculate_valuation_scenarios 直接使用。"""

    if model == "growth_tech":
        if annual_roe is not None and annual_roe >= 20:
            pe_c, pe_n, pe_o = 22.0, 30.0, 40.0
            pb_c, pb_n, pb_o = 2.5, 3.5, 4.5
        elif annual_roe is not None and annual_roe >= 15:
            pe_c, pe_n, pe_o = 18.0, 26.0, 35.0
            pb_c, pb_n, pb_o = 2.0, 3.0, 4.0
        elif annual_roe is not None and annual_roe >= 10:
            pe_c, pe_n, pe_o = 15.0, 22.0, 30.0
            pb_c, pb_n, pb_o = 1.8, 2.6, 3.5
        else:
            pe_c, pe_n, pe_o = 12.0, 18.0, 25.0
            pb_c, pb_n, pb_o = 1.5, 2.2, 3.0

        return {
            "name": "成长科技估值（成长溢价PE+PB）",
            "short_name": "科技成长",
            "method": "成长溢价PE + PB",
            "conservative_pe": pe_c,
            "normal_pe": pe_n,
            "optimistic_pe": pe_o,
            "conservative_pb": pb_c,
            "normal_pb": pb_n,
            "optimistic_pb": pb_o,
            "pe_weight": 0.80,
            "pb_weight": 0.20,
            "note": "V16.6.1科技成长模型：提高成长公司的合理PE区间，但尚未直接使用未经验证的未来利润/PEG，因此不会无限抬高目标价。"
        }

    if model == "insurance":
        return {
            "name": "保险综合估值（PB主导）",
            "short_name": "保险",
            "method": "PB主导 + 低权重PE",
            "conservative_pe": 6.0,
            "normal_pe": 8.0,
            "optimistic_pe": 10.0,
            "conservative_pb": 0.75,
            "normal_pb": 0.95,
            "optimistic_pb": 1.15,
            "pe_weight": 0.15,
            "pb_weight": 0.85,
            "note": "保险公司估值应重点参考PB、内含价值和新业务价值；当前版本尚未接入EV/NBV，因此仅作为初版估值。"
        }

    if model == "bank":
        return {
            "name": "银行估值（PB/ROE主导）",
            "short_name": "银行",
            "method": "PB主导 + 辅助PE",
            "conservative_pe": 5.0,
            "normal_pe": 6.0,
            "optimistic_pe": 7.5,
            "conservative_pb": 0.55,
            "normal_pb": 0.75,
            "optimistic_pb": 0.95,
            "pe_weight": 0.15,
            "pb_weight": 0.85,
            "note": "银行业更关注ROE、资产质量、PB及股息率，不能直接套用普通制造业PE。"
        }

    if model == "broker":
        return {
            "name": "券商估值（PB周期主导）",
            "short_name": "券商",
            "method": "PB主导 + 周期PE",
            "conservative_pe": 10.0,
            "normal_pe": 13.0,
            "optimistic_pe": 16.0,
            "conservative_pb": 0.9,
            "normal_pb": 1.2,
            "optimistic_pb": 1.5,
            "pe_weight": 0.35,
            "pb_weight": 0.65,
            "note": "券商利润具有明显周期性，PB和资本金回报率通常比单年PE更有参考意义。"
        }

    if model == "cyclical":
        return {
            "name": "周期股估值（正常化利润）",
            "short_name": "周期",
            "method": "正常化PE + PB",
            "conservative_pe": 8.0,
            "normal_pe": 10.0,
            "optimistic_pe": 13.0,
            "conservative_pb": 1.0,
            "normal_pb": 1.3,
            "optimistic_pb": 1.7,
            "pe_weight": 0.40,
            "pb_weight": 0.60,
            "note": "周期行业当前利润可能处于周期高低点，必须防止用景气高点利润高估公司价值。"
        }

    if annual_roe is not None:
        if annual_roe >= 20:
            pe_c, pe_n, pe_o = 14.0, 18.0, 22.0
            pe_weight, pb_weight = 0.75, 0.25
        elif annual_roe >= 15:
            pe_c, pe_n, pe_o = 13.0, 17.0, 21.0
            pe_weight, pb_weight = 0.70, 0.30
        elif annual_roe >= 10:
            pe_c, pe_n, pe_o = 10.0, 14.0, 18.0
            pe_weight, pb_weight = 0.60, 0.40
        else:
            pe_c, pe_n, pe_o = 8.0, 11.0, 14.0
            pe_weight, pb_weight = 0.50, 0.50
    else:
        pe_c, pe_n, pe_o = 10.0, 14.0, 18.0
        pe_weight, pb_weight = 0.60, 0.40

    return {
        "name": "普通成长/制造估值",
        "short_name": "普通",
        "method": "PE + PB",
        "conservative_pe": pe_c,
        "normal_pe": pe_n,
        "optimistic_pe": pe_o,
        "conservative_pb": 1.5,
        "normal_pb": 2.0,
        "optimistic_pb": 2.5,
        "pe_weight": pe_weight,
        "pb_weight": pb_weight,
        "note": "普通公司沿用V16的ROE驱动PE/PB综合估值。"
    }
