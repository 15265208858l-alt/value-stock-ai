"""
ValueStock AI
行业与同行股票池 V2

目标：
稳定提供主要A股公司的同行股票池。

原则：
1. 不依赖不稳定的实时行业反查接口
2. 采用维护型行业股票池
3. 自动根据股票代码匹配行业
4. 自动排除目标股票
5. 自动返回最多5只同行
"""

# =========================================================
# 1. 行业股票池
# =========================================================

INDUSTRY_STOCK_POOLS = {

    "电力设备": [

        ("600089", "特变电工"),
        ("000400", "许继电气"),
        ("600312", "平高电气"),
        ("601179", "中国西电"),
        ("002028", "思源电气"),
        ("600406", "国电南瑞"),
        ("300274", "阳光电源"),
        ("688390", "固德威")

    ],

    "家用电器": [

        ("000333", "美的集团"),
        ("000651", "格力电器"),
        ("600690", "海尔智家"),
        ("002032", "苏泊尔"),
        ("002050", "三花智控"),
        ("000921", "海信家电")

    ],

    "有色金属": [

        ("601899", "紫金矿业"),
        ("603993", "洛阳钼业"),
        ("600547", "山东黄金"),
        ("600489", "中金黄金"),
        ("600111", "北方稀土"),
        ("000878", "云南铜业")

    ],

    "计算机": [

        ("000938", "紫光股份"),
        ("000977", "浪潮信息"),
        ("600845", "宝信软件"),
        ("600570", "恒生电子"),
        ("002410", "广联达"),
        ("300454", "深信服")

    ],

    "养殖": [

        ("002714", "牧原股份"),
        ("300498", "温氏股份"),
        ("002567", "唐人神"),
        ("002458", "益生股份"),
        ("000876", "新希望"),
        ("002100", "天康生物")

    ]

}


# =========================================================
# 2. 股票 → 行业映射
# =========================================================

STOCK_INDUSTRY_MAP = {}


for industry_name, stocks in INDUSTRY_STOCK_POOLS.items():

    for code, name in stocks:

        STOCK_INDUSTRY_MAP[code] = {
            "industry": industry_name,
            "name": name
        }


# =========================================================
# 3. 清洗股票代码
# =========================================================

def clean_stock_code(code):

    if code is None:
        return ""

    code = str(code).strip()

    if len(code) != 6:
        return ""

    if not code.isdigit():
        return ""

    return code


# =========================================================
# 4. 获取股票所属行业
# =========================================================

def get_stock_industry(stock_code):

    stock_code = clean_stock_code(
        stock_code
    )

    if not stock_code:
        return None

    result = STOCK_INDUSTRY_MAP.get(
        stock_code
    )

    if result is None:
        return None

    return result["industry"]


# =========================================================
# 5. 获取股票名称
# =========================================================

def get_stock_name(stock_code):

    stock_code = clean_stock_code(
        stock_code
    )

    if not stock_code:
        return None

    result = STOCK_INDUSTRY_MAP.get(
        stock_code
    )

    if result is None:
        return None

    return result["name"]


# =========================================================
# 6. 获取行业股票池
# =========================================================

def get_industry_stock_pool(
    industry_name
):

    if not industry_name:
        return []

    stocks = (
        INDUSTRY_STOCK_POOLS.get(
            industry_name,
            []
        )
    )

    return [
        code
        for code, name in stocks
    ]


# =========================================================
# 7. 自动寻找同行
# =========================================================

def get_peer_candidates(
    stock_code,
    max_peers=5
):

    stock_code = clean_stock_code(
        stock_code
    )

    if not stock_code:

        return {
            "industry": None,
            "name": None,
            "peers": []
        }


    industry_name = (
        get_stock_industry(
            stock_code
        )
    )


    stock_name = (
        get_stock_name(
            stock_code
        )
    )


    if industry_name is None:

        return {
            "industry": None,
            "name": stock_name,
            "peers": []
        }


    pool = (
        get_industry_stock_pool(
            industry_name
        )
    )


    peers = [

        code

        for code in pool

        if code != stock_code

    ]


    peers = peers[
        :max_peers
    ]


    return {

        "industry":
            industry_name,

        "name":
            stock_name,

        "peers":
            peers
    }


# =========================================================
# 8. 显示行业信息
# =========================================================

def get_industry_info(
    stock_code
):

    result = (
        get_peer_candidates(
            stock_code
        )
    )

    return {

        "stock_code":
            clean_stock_code(
                stock_code
            ),

        "stock_name":
            result.get(
                "name"
            ),

        "industry":
            result.get(
                "industry"
            ),

        "peers":
            result.get(
                "peers",
                []
            )
    }
