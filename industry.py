"""
ValueStock AI
行业与同行股票池 V3.5

更新：
- 001339智微智能归入AI/算力，避免被错误归入传统软件/计算机估值池。
- AI/算力同行池覆盖服务器、ICT基础设施、算力芯片等可比公司。
- 自动同行默认最多2只，保证运行稳定。
"""

INDUSTRY_STOCK_POOLS = {
    "电力设备": [("600089", "特变电工"), ("000400", "许继电气"), ("600312", "平高电气"), ("601179", "中国西电"), ("002028", "思源电气"), ("600406", "国电南瑞"), ("300274", "阳光电源"), ("688390", "固德威")],
    "家用电器": [("000333", "美的集团"), ("000651", "格力电器"), ("600690", "海尔智家"), ("002032", "苏泊尔"), ("002050", "三花智控"), ("000921", "海信家电")],
    "有色金属": [("601899", "紫金矿业"), ("603993", "洛阳钼业"), ("600547", "山东黄金"), ("600489", "中金黄金"), ("600111", "北方稀土"), ("000878", "云南铜业")],
    "计算机": [("000938", "紫光股份"), ("000977", "浪潮信息"), ("600845", "宝信软件"), ("600570", "恒生电子"), ("002410", "广联达"), ("300454", "深信服"), ("002230", "科大讯飞"), ("688111", "金山办公")],
    "光通信": [("300308", "中际旭创"), ("300502", "新易盛"), ("300394", "天孚通信"), ("002281", "光迅科技"), ("000988", "华工科技"), ("603083", "剑桥科技")],
    "半导体": [("002156", "通富微电"), ("688981", "中芯国际"), ("688041", "海光信息"), ("688008", "澜起科技"), ("002371", "北方华创"), ("603986", "兆易创新"), ("600584", "长电科技"), ("600460", "士兰微")],
    "AI/算力": [("001339", "智微智能"), ("000977", "浪潮信息"), ("601138", "工业富联"), ("000938", "紫光股份"), ("688041", "海光信息"), ("000034", "神州数码"), ("688256", "寒武纪")],
    "保险": [("601318", "中国平安"), ("601601", "中国太保"), ("601336", "新华保险"), ("601628", "中国人寿"), ("000627", "天茂集团")],
    "养殖": [("002714", "牧原股份"), ("300498", "温氏股份"), ("002567", "唐人神"), ("002458", "益生股份"), ("000876", "新希望"), ("002100", "天康生物")],
}

STOCK_INDUSTRY_MAP = {}
for industry_name, stocks in INDUSTRY_STOCK_POOLS.items():
    for code, name in stocks:
        STOCK_INDUSTRY_MAP.setdefault(code, {"industry": industry_name, "name": name})

for code, industry in {
    "300308": "光通信", "300502": "光通信", "300394": "光通信",
    "002156": "半导体", "688981": "半导体", "688041": "半导体",
    "000938": "计算机", "000977": "AI/算力", "001339": "AI/算力", "601138": "AI/算力",
    "601318": "保险", "601601": "保险", "601336": "保险", "601628": "保险",
}.items():
    if code in STOCK_INDUSTRY_MAP:
        STOCK_INDUSTRY_MAP[code]["industry"] = industry


def clean_stock_code(code):
    if code is None:
        return ""
    code = str(code).strip()
    return code if len(code) == 6 and code.isdigit() else ""


def get_stock_industry(stock_code):
    return (STOCK_INDUSTRY_MAP.get(clean_stock_code(stock_code)) or {}).get("industry")


def get_stock_name(stock_code):
    return (STOCK_INDUSTRY_MAP.get(clean_stock_code(stock_code)) or {}).get("name")


def get_industry_stock_pool(industry_name):
    return [code for code, _ in INDUSTRY_STOCK_POOLS.get(industry_name, [])]


def get_peer_candidates(stock_code, max_peers=5):
    code = clean_stock_code(stock_code)
    if not code:
        return {"industry": None, "name": None, "peers": []}
    industry = get_stock_industry(code)
    name = get_stock_name(code)
    if not industry:
        return {"industry": None, "name": name, "peers": []}
    peers = [x for x in get_industry_stock_pool(industry) if x != code]
    auto_limit = min(max(int(max_peers or 5), 0), 2)
    return {"industry": industry, "name": name, "peers": peers[:auto_limit]}


def get_industry_info(stock_code):
    result = get_peer_candidates(stock_code)
    return {
        "stock_code": clean_stock_code(stock_code),
        "stock_name": result.get("name"),
        "industry": result.get("industry"),
        "peers": result.get("peers", []),
    }
