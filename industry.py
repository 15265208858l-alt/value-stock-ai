"""
ValueStock AI
行业识别与自动同行模块 V1

功能：
1. 获取A股行业分类
2. 根据股票代码寻找所属行业
3. 自动建立同行股票池
4. 排除目标公司自身
5. 返回最基础的同行候选列表

说明：
当前版本优先保证稳定性。
如果行业接口暂时不可用，返回空结果，
不会影响主程序运行。
"""

import akshare as ak


# =========================================================
# 1. 基础工具
# =========================================================

def clean_stock_code(code):
    """清理股票代码"""

    if code is None:
        return ""

    code = str(code).strip()

    if len(code) != 6:
        return ""

    if not code.isdigit():
        return ""

    return code


# =========================================================
# 2. 获取行业分类
# =========================================================

def get_industry_data():
    """
    获取A股行业分类数据。

    返回：
        DataFrame
        失败返回None
    """

    # -----------------------------------------------------
    # 主接口
    # -----------------------------------------------------

    try:

        data = ak.stock_board_industry_name_em()

        if (
            data is not None
            and not data.empty
        ):

            return data

    except Exception:

        pass

    # -----------------------------------------------------
    # 备用接口
    # -----------------------------------------------------

    try:

        data = ak.stock_board_industry_cons_em(
            symbol="电力设备"
        )

        if (
            data is not None
            and not data.empty
        ):

            return data

    except Exception:

        pass

    return None


# =========================================================
# 3. 尝试获取公司行业
# =========================================================

def get_stock_industry(
    stock_code
):
    """
    根据股票代码寻找行业。

    注意：
    不同AKShare版本行业字段可能不同，
    所以这里采用多种字段兼容。
    """

    stock_code = clean_stock_code(
        stock_code
    )

    if not stock_code:

        return None


    # -----------------------------------------------------
    # 方法一：股票信息接口
    # -----------------------------------------------------

    try:

        data = ak.stock_individual_info_em(
            symbol=stock_code
        )

        if (
            data is not None
            and not data.empty
        ):

            # 常见格式：
            # item / value

            name_col = None
            value_col = None

            if "item" in data.columns:
                name_col = "item"

            elif "项目" in data.columns:
                name_col = "项目"


            if "value" in data.columns:
                value_col = "value"

            elif "值" in data.columns:
                value_col = "值"


            if (
                name_col is not None
                and value_col is not None
            ):

                rows = data[
                    data[name_col]
                    .astype(str)
                    .str.contains(
                        "行业",
                        na=False
                    )
                ]

                if not rows.empty:

                    industry = str(
                        rows.iloc[0][
                            value_col
                        ]
                    )

                    if industry:

                        return industry

    except Exception:

        pass


    # -----------------------------------------------------
    # 方法二：行业板块成分反查
    # -----------------------------------------------------

    try:

        industries = (
            ak.stock_board_industry_name_em()
        )

        if (
            industries is None
            or industries.empty
        ):

            return None


        name_col = None

        for col in [
            "板块名称",
            "行业名称",
            "名称"
        ]:

            if col in industries.columns:

                name_col = col

                break


        if name_col is None:

            return None


        # 当前接口通常只能拿到行业板块名称，
        # 因此这里只保留行业名称候选。
        #
        # 真正的股票归属确认在下一步
        # 自动同行模块中进一步处理。

        return None

    except Exception:

        pass


    return None


# =========================================================
# 4. 获取行业板块股票
# =========================================================

def get_industry_stocks(
    industry_name
):
    """
    获取指定行业板块的股票。

    参数：
        industry_name：行业名称

    返回：
        股票代码列表
    """

    if not industry_name:

        return []


    try:

        # 行业名称可能与实际板块名称略有差异。
        #
        # 先获取所有行业板块。

        industries = (
            ak.stock_board_industry_name_em()
        )


        if (
            industries is None
            or industries.empty
        ):

            return []


        name_col = None


        for col in [
            "板块名称",
            "行业名称",
            "名称"
        ]:

            if col in industries.columns:

                name_col = col

                break


        if name_col is None:

            return []


        industry_names = (
            industries[name_col]
            .astype(str)
            .tolist()
        )


        # -------------------------------------------------
        # 模糊匹配行业
        # -------------------------------------------------

        matched_name = None


        for name in industry_names:

            if industry_name in name:

                matched_name = name

                break


            if name in industry_name:

                matched_name = name

                break


        if matched_name is None:

            return []


        # -------------------------------------------------
        # 获取行业成分
        # -------------------------------------------------

        stocks = (
            ak.stock_board_industry_cons_em(
                symbol=matched_name
            )
        )


        if (
            stocks is None
            or stocks.empty
        ):

            return []


        code_col = None


        for col in [
            "代码",
            "股票代码"
        ]:

            if col in stocks.columns:

                code_col = col

                break


        if code_col is None:

            return []


        codes = (
            stocks[code_col]
            .astype(str)
            .str.strip()
            .tolist()
        )


        return [
            code
            for code in codes
            if len(code) == 6
            and code.isdigit()
        ]


    except Exception:

        return []


# =========================================================
# 5. 自动建立同行池
# =========================================================

def get_peer_candidates(
    stock_code,
    max_peers=5
):
    """
    自动寻找同行股票。

    返回：

    {
        "industry": 行业名称,
        "peers": [
            股票代码...
        ]
    }
    """

    stock_code = clean_stock_code(
        stock_code
    )

    if not stock_code:

        return {
            "industry": None,
            "peers": []
        }


    industry_name = (
        get_stock_industry(
            stock_code
        )
    )


    if not industry_name:

        return {
            "industry": None,
            "peers": []
        }


    stocks = (
        get_industry_stocks(
            industry_name
        )
    )


    if not stocks:

        return {
            "industry":
                industry_name,

            "peers": []
        }


    # -----------------------------------------------------
    # 排除目标公司
    # -----------------------------------------------------

    peers = [

        code

        for code in stocks

        if code != stock_code

    ]


    # -----------------------------------------------------
    # 最多取 max_peers
    # -----------------------------------------------------

    peers = peers[
        :max_peers
    ]


    return {

        "industry":
            industry_name,

        "peers":
            peers
    }
