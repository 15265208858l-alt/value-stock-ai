"""行业自适应估值配置。估值配置只计算参数，不发起网络请求。"""
LAST_STOCK_CODE = None
LAST_MODEL = "general"

def _contains(text, keywords):
    text = str(text or "")
    return any(k in text for k in keywords)

def detect_valuation_model(industry=None, market_industry=None, stock_code=None, override="自动识别"):
    global LAST_STOCK_CODE, LAST_MODEL
    LAST_STOCK_CODE = str(stock_code or "").strip()
    mapping = {"普通成长/制造":"general","银行":"bank","保险":"insurance","券商":"broker","周期":"cyclical","成长科技":"growth_tech"}
    if override in mapping:
        LAST_MODEL = mapping[override]
        return LAST_MODEL
    text = f"{industry or ''} {market_industry or ''}"
    if _contains(text,["半导体","芯片","电子","光通信","通信设备","通信服务","AI","人工智能","算力","机器人","软件","计算机","云计算","数据中心","自动化","消费电子","信息技术","元器件","集成电路","服务器","ICT","互联网","数字经济"]):
        LAST_MODEL="growth_tech"; return LAST_MODEL
    if _contains(text,["保险","寿险","财险","健康险"]): LAST_MODEL="insurance"; return LAST_MODEL
    if _contains(text,["银行","商业银行"]): LAST_MODEL="bank"; return LAST_MODEL
    if _contains(text,["证券","券商"]): LAST_MODEL="broker"; return LAST_MODEL
    if _contains(text,["煤炭","钢铁","有色","石油","石化","化工","铝","铜","黄金","稀土","水泥"]): LAST_MODEL="cyclical"; return LAST_MODEL
    insurance={"601318","601336","601601","000627","000628"}
    bank={"000001","002142","002807","600000","600015","600016","600036","600919","601009","601128","601166","601169","601229","601288","601328","601398","601658","601818","601939","601988","601997","601998"}
    broker={"000166","000686","000728","000750","000776","002500","600030","600061","600109","600837","601066","601099","601211","601377","601555","601688","601878","601881","601901","601995"}
    tech={"001339","300308","300502","300394","000938","000977","601138","688041","603019","603516","600845","600570","600588","600728","688981","688256","688008","688126","002371","002156","688036","600584","600460","603986","688099","688012","688019","688498","688111","002230","300454","300496","300674","300017","002153","300124","688017","002747","002472","300024","601127"}
    if LAST_STOCK_CODE in insurance: LAST_MODEL="insurance"
    elif LAST_STOCK_CODE in bank: LAST_MODEL="bank"
    elif LAST_STOCK_CODE in broker: LAST_MODEL="broker"
    elif LAST_STOCK_CODE in tech or LAST_STOCK_CODE.startswith("688"): LAST_MODEL="growth_tech"
    else: LAST_MODEL="general"
    return LAST_MODEL

def get_valuation_config(model, annual_roe=None):
    global LAST_MODEL
    LAST_MODEL=model
    if model=="growth_tech":
        if annual_roe is not None and annual_roe>=20: pe_c,pe_n,pe_o,pb_c,pb_n,pb_o=22,30,40,2.5,3.5,4.5
        elif annual_roe is not None and annual_roe>=15: pe_c,pe_n,pe_o,pb_c,pb_n,pb_o=18,26,35,2,3,4
        elif annual_roe is not None and annual_roe>=10: pe_c,pe_n,pe_o,pb_c,pb_n,pb_o=15,22,30,1.8,2.6,3.5
        else: pe_c,pe_n,pe_o,pb_c,pb_n,pb_o=12,18,25,1.5,2.2,3
        return {"name":"成长科技估值（TTM成长PE+PB）","short_name":"科技成长","method":"TTM成长PE + PB","conservative_pe":pe_c,"normal_pe":pe_n,"optimistic_pe":pe_o,"conservative_pb":pb_c,"normal_pb":pb_n,"optimistic_pb":pb_o,"pe_weight":.80,"pb_weight":.20,"eps_multiplier":1.0,"earnings_basis":"由主流程计算","ttm_eps":None,"forward_eps_annualized":None,"note":"成长科技估值优先采用主流程计算的TTM/正常化EPS，不直接把未经验证的未来利润当作事实。"}
    if model=="insurance": return {"name":"保险综合估值（PB主导）","short_name":"保险","method":"PB主导 + 低权重PE","conservative_pe":6,"normal_pe":8,"optimistic_pe":10,"conservative_pb":.75,"normal_pb":.95,"optimistic_pb":1.15,"pe_weight":.15,"pb_weight":.85,"eps_multiplier":1.0,"earnings_basis":"FY年度EPS","ttm_eps":None,"forward_eps_annualized":None,"note":"保险公司估值应重点参考PB、内含价值和新业务价值；当前EV/NBV仍未接入。"}
    if model=="bank": return {"name":"银行估值（PB/ROE主导）","short_name":"银行","method":"PB主导 + 辅助PE","conservative_pe":5,"normal_pe":6,"optimistic_pe":7.5,"conservative_pb":.55,"normal_pb":.75,"optimistic_pb":.95,"pe_weight":.15,"pb_weight":.85,"eps_multiplier":1.0,"earnings_basis":"FY年度EPS","ttm_eps":None,"forward_eps_annualized":None,"note":"银行业更关注ROE、资产质量、PB及股息率。"}
    if model=="broker": return {"name":"券商估值（PB周期主导）","short_name":"券商","method":"PB主导 + 周期PE","conservative_pe":10,"normal_pe":13,"optimistic_pe":16,"conservative_pb":.9,"normal_pb":1.2,"optimistic_pb":1.5,"pe_weight":.35,"pb_weight":.65,"eps_multiplier":1.0,"earnings_basis":"FY年度EPS","ttm_eps":None,"forward_eps_annualized":None,"note":"券商利润具有明显周期性，PB和资本金回报率通常比单年PE更有参考意义。"}
    if model=="cyclical": return {"name":"周期股估值（正常化利润）","short_name":"周期","method":"正常化PE + PB","conservative_pe":8,"normal_pe":10,"optimistic_pe":13,"conservative_pb":1,"normal_pb":1.3,"optimistic_pb":1.7,"pe_weight":.40,"pb_weight":.60,"eps_multiplier":1.0,"earnings_basis":"FY年度EPS","ttm_eps":None,"forward_eps_annualized":None,"note":"周期行业当前利润可能处于周期高低点，必须防止用景气高点利润高估公司价值。"}
    if annual_roe is not None and annual_roe>=20: pe_c,pe_n,pe_o,pw,bw=14,18,22,.75,.25
    elif annual_roe is not None and annual_roe>=15: pe_c,pe_n,pe_o,pw,bw=13,17,21,.70,.30
    elif annual_roe is not None and annual_roe>=10: pe_c,pe_n,pe_o,pw,bw=10,14,18,.60,.40
    else: pe_c,pe_n,pe_o,pw,bw=8,11,14,.50,.50
    return {"name":"普通成长/制造估值","short_name":"普通","method":"PE + PB","conservative_pe":pe_c,"normal_pe":pe_n,"optimistic_pe":pe_o,"conservative_pb":1.5,"normal_pb":2.0,"optimistic_pb":2.5,"pe_weight":pw,"pb_weight":bw,"eps_multiplier":1.0,"earnings_basis":"FY年度EPS","ttm_eps":None,"forward_eps_annualized":None,"note":"普通公司沿用ROE驱动PE/PB综合估值。"}
