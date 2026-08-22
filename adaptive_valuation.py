"""
ValueStock AI
行业自适应估值引擎 V16.7

核心升级：
1. 普通公司、银行、保险、券商、周期股继续使用差异化估值。
2. 成长科技模型加入TTM EPS估值基础，减少历史年度EPS滞后。
3. Forward EPS只做年化观察，不直接虚构未来利润。
4. 数据不足时自动回退，不让估值模块导致程序中断。
"""

try:
    from data import load_stock_data
    from earnings_basis import build_earnings_basis
except Exception:
    load_stock_data = None
    build_earnings_basis = None

LAST_STOCK_CODE = None
LAST_MODEL = "general"
LAST_EARNINGS_BASIS = {
    "annual_eps": None,
    "latest_eps": None,
    "prior_same_period_eps": None,
    "ttm_eps": None,
    "forward_eps_annualized": None,
    "valuation_eps": None,
    "basis": "FY年度EPS",
    "confidence": "低",
    "note": "数据不足。",
}


def _contains(text, keywords):
    text = str(text or "")
    return any(keyword in text for keyword in keywords)


def detect_valuation_model(industry=None, market_industry=None, stock_code=None, override="自动识别"):
    global LAST_STOCK_CODE, LAST_MODEL
    LAST_STOCK_CODE = str(stock_code or "").strip()

    override_map = {
        "普通成长/制造": "general",
        "银行": "bank",
        "保险": "insurance",
        "券商": "broker",
        "周期": "cyclical",
        "成长科技": "growth_tech",
    }

    if override in override_map:
        LAST_MODEL = override_map[override]
        return LAST_MODEL

    text = f"{industry or ''} {market_industry or ''}"

    if _contains(text, [
        "半导体", "芯片", "电子", "光通信", "通信设备", "通信服务",
        "AI", "人工智能", "算力", "机器人", "软件", "计算机",
        "云计算", "数据中心", "自动化", "消费电子", "信息技术",
        "元器件", "集成电路", "IT", "互联网", "数字经济"
    ]):
        LAST_MODEL = "growth_tech"
        return LAST_MODEL

    if _contains(text, ["保险", "寿险", "财险", "健康险"]):
        LAST_MODEL = "insurance"
        return LAST_MODEL
    if _contains(text, ["银行", "商业银行"]):
        LAST_MODEL = "bank"
        return LAST_MODEL
    if _contains(text, ["证券", "券商"]):
        LAST_MODEL = "broker"
        return LAST_MODEL
    if _contains(text, ["煤炭", "钢铁", "有色", "石油", "石化", "化工", "铝", "铜", "黄金", "稀土", "水泥"]):
        LAST_MODEL = "cyclical"
        return LAST_MODEL

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
    growth_tech_codes = {
        "300308", "300502", "300394", "000938", "000977", "601138", "688041", "603019",
        "603516", "600845", "600570", "600588", "600728", "688981", "688256", "688008",
        "688126", "002371", "002156", "688036", "600584", "600460", "603986", "688099",
        "688012", "688019", "688498", "688111", "002230", "300454", "300496", "300674",
        "300017", "002153", "300124", "688017", "002747", "002472", "300024", "601127"
    }

    if LAST_STOCK_CODE in insurance_codes:
        LAST_MODEL = "insurance"
    elif LAST_STOCK_CODE in bank_codes:
        LAST_MODEL = "bank"
    elif LAST_STOCK_CODE in broker_codes:
        LAST_MODEL = "broker"
    elif LAST_STOCK_CODE in growth_tech_codes or LAST_STOCK_CODE.startswith("688"):
        LAST_MODEL = "growth_tech"
    else:
        LAST_MODEL = "general"

    return LAST_MODEL


def _refresh_growth_earnings_basis():
    global LAST_EARNINGS_BASIS

    if LAST_MODEL != "growth_tech":
        return LAST_EARNINGS_BASIS
    if load_stock_data is None or build_earnings_basis is None or not LAST_STOCK_CODE:
        return LAST_EARNINGS_BASIS

    try:
        stock_data = load_stock_data(LAST_STOCK_CODE)
        indicators = stock_data.get("indicators") if stock_data else None
        if indicators is not None and not indicators.empty:
            LAST_EARNINGS_BASIS = build_earnings_basis(indicators)
    except Exception:
        pass

    return LAST_EARNINGS_BASIS


def get_valuation_config(model, annual_roe=None):
    global LAST_MODEL, LAST_EARNINGS_BASIS
    LAST_MODEL = model

    if model == "growth_tech":
        earnings_basis = _refresh_growth_earnings_basis()

        annual_eps = earnings_basis.get("annual_eps")
        valuation_eps = earnings_basis.get("valuation_eps")
        earnings_multiplier = 1.0

        if annual_eps is not None and valuation_eps is not None and annual_eps > 0 and valuation_eps > 0:
            earnings_multiplier = max(1.0, min(3.0, valuation_eps / annual_eps))

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

        forward_text = earnings_basis.get("forward_eps_annualized")
        note = (
            f"V16.7成长科技模型：估值优先采用{earnings_basis.get('basis', 'FY年度EPS')}，"
            "不直接把未经验证的未来利润当作事实。"
        )
        if forward_text is not None:
            note += f" 最新报告期年化EPS观察值约{forward_text:.2f}元，仅作参考。"

        return {
            "name": "成长科技估值（TTM成长PE+PB）",
            "short_name": "科技成长",
            "method": "TTM成长PE + PB",
            "conservative_pe": pe_c,
            "normal_pe": pe_n,
            "optimistic_pe": pe_o,
            "conservative_pb": pb_c,
            "normal_pb": pb_n,
            "optimistic_pb": pb_o,
            "pe_weight": 0.80,
            "pb_weight": 0.20,
            "eps_multiplier": earnings_multiplier,
            "earnings_basis": earnings_basis.get("basis", "FY年度EPS"),
            "ttm_eps": earnings_basis.get("ttm_eps"),
            "forward_eps_annualized": forward_text,
            "note": note,
        }

    if model == "insurance":
        return {
            "name": "保险综合估值（PB主导）", "short_name": "保险", "method": "PB主导 + 低权重PE",
            "conservative_pe": 6.0, "normal_pe": 8.0, "optimistic_pe": 10.0,
            "conservative_pb": 0.75, "normal_pb": 0.95, "optimistic_pb": 1.15,
            "pe_weight": 0.15, "pb_weight": 0.85, "eps_multiplier": 1.0,
            "earnings_basis": "FY年度EPS", "ttm_eps": None, "forward_eps_annualized": None,
            "note": "保险公司估值应重点参考PB、内含价值和新业务价值；当前EV/NBV仍未接入。"
        }

    if model == "bank":
        return {
            "name": "银行估值（PB/ROE主导）", "short_name": "银行", "method": "PB主导 + 辅助PE",
            "conservative_pe": 5.0, "normal_pe": 6.0, "optimistic_pe": 7.5,
            "conservative_pb": 0.55, "normal_pb": 0.75, "optimistic_pb": 0.95,
            "pe_weight": 0.15, "pb_weight": 0.85, "eps_multiplier": 1.0,
            "earnings_basis": "FY年度EPS", "ttm_eps": None, "forward_eps_annualized": None,
            "note": "银行业更关注ROE、资产质量、PB及股息率。"
        }

    if model == "broker":
        return {
            "name": "券商估值（PB周期主导）", "short_name": "券商", "method": "PB主导 + 周期PE",
            "conservative_pe": 10.0, "normal_pe": 13.0, "optimistic_pe": 16.0,
            "conservative_pb": 0.9, "normal_pb": 1.2, "optimistic_pb": 1.5,
            "pe_weight": 0.35, "pb_weight": 0.65, "eps_multiplier": 1.0,
            "earnings_basis": "FY年度EPS", "ttm_eps": None, "forward_eps_annualized": None,
            "note": "券商利润具有明显周期性，PB和资本金回报率通常比单年PE更有参考意义。"
        }

    if model == "cyclical":
        return {
            "name": "周期股估值（正常化利润）", "short_name": "周期", "method": "正常化PE + PB",
            "conservative_pe": 8.0, "normal_pe": 10.0, "optimistic_pe": 13.0,
            "conservative_pb": 1.0, "normal_pb": 1.3, "optimistic_pb": 1.7,
            "pe_weight": 0.40, "pb_weight": 0.60, "eps_multiplier": 1.0,
            "earnings_basis": "FY年度EPS", "ttm_eps": None, "forward_eps_annualized": None,
            "note": "周期行业当前利润可能处于周期高低点，必须防止用景气高点利润高估公司价值。"
        }

    if annual_roe is not None:
        if annual_roe >= 20:
            pe_c, pe_n, pe_o, pe_weight, pb_weight = 14.0, 18.0, 22.0, 0.75, 0.25
        elif annual_roe >= 15:
            pe_c, pe_n, pe_o, pe_weight, pb_weight = 13.0, 17.0, 21.0, 0.70, 0.30
        elif annual_roe >= 10:
            pe_c, pe_n, pe_o, pe_weight, pb_weight = 10.0, 14.0, 18.0, 0.60, 0.40
        else:
            pe_c, pe_n, pe_o, pe_weight, pb_weight = 8.0, 11.0, 14.0, 0.50, 0.50
    else:
        pe_c, pe_n, pe_o, pe_weight, pb_weight = 10.0, 14.0, 18.0, 0.60, 0.40

    return {
        "name": "普通成长/制造估值", "short_name": "普通", "method": "PE + PB",
        "conservative_pe": pe_c, "normal_pe": pe_n, "optimistic_pe": pe_o,
        "conservative_pb": 1.5, "normal_pb": 2.0, "optimistic_pb": 2.5,
        "pe_weight": pe_weight, "pb_weight": pb_weight, "eps_multiplier": 1.0,
        "earnings_basis": "FY年度EPS", "ttm_eps": None, "forward_eps_annualized": None,
        "note": "普通公司沿用ROE驱动PE/PB综合估值。"
    }
