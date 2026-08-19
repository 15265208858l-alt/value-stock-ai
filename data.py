"""
ValueStock AI
数据中心模块 V1

统一负责：
1. A股实时行情
2. A股历史行情
3. 财务指标
4. 三大财务报表

原则：
- 数据获取和数据分析分离
- 所有接口统一在这里管理
- 接口失败尽量自动使用备用接口
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


def get_market_code(stock_code):
    """
    返回：
    sh600000
    sz000001
    bjxxxxxx
    """

    if stock_code.startswith(("6", "68")):
        return "sh" + stock_code

    if stock_code.startswith(("0", "3")):
        return "sz" + stock_code

    if stock_code.startswith(("4", "8")):
        return "bj" + stock_code

    return stock_code


def get_symbol_code(stock_code):
    """
    部分AKShare接口使用：

    SH600000
    SZ000001
    """

    if stock_code.startswith(("6", "68")):
        return "SH" + stock_code

    if stock_code.startswith(("0", "3")):
        return "SZ" + stock_code

    if stock_code.startswith(("4", "8")):
        return "BJ" + stock_code

    return stock_code


# =========================================================
# 2. 实时行情
# =========================================================

def get_realtime_market(stock_code):
    """
    获取A股实时行情

    返回：
        dict
        获取失败返回None
    """

    stock_code = clean_stock_code(
        stock_code
    )

    if not stock_code:
        return None

    try:

        data = ak.stock_zh_a_spot_em()

        if (
            data is None
            or data.empty
        ):

            return None

        code_columns = [
            "代码",
            "股票代码"
        ]

        code_col = None

        for col in code_columns:

            if col in data.columns:

                code_col = col

                break

        if code_col is None:

            return None

        result = data[
            data[code_col].astype(str)
            == stock_code
        ]

        if result.empty:

            return None

        return result.iloc[0].to_dict()

    except Exception:

        return None


# =========================================================
# 3. 历史行情
# =========================================================

def get_history_data(
    stock_code,
    start_date="20200101",
    end_date="20500101"
):
    """
    获取历史行情

    第一接口：
        东方财富

    失败后：
        腾讯备用接口
    """

    stock_code = clean_stock_code(
        stock_code
    )

    if not stock_code:
        return None


    # -----------------------------------------------------
    # 主接口
    # -----------------------------------------------------

    try:

        data = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=""
        )

        if (
            data is not None
            and not data.empty
        ):

            return data

    except Exception:

        pass


    # -----------------------------------------------------
    # 备用接口：腾讯
    # -----------------------------------------------------

    try:

        data = ak.stock_zh_a_hist_tx(
            symbol=get_market_code(
                stock_code
            ),
            start_date=start_date,
            end_date=end_date,
            adjust=""
        )

        if (
            data is not None
            and not data.empty
        ):

            return data

    except Exception:

        pass


    return None


def get_latest_price(history):
    """
    从历史行情获取最近收盘价
    """

    if (
        history is None
        or history.empty
    ):

        return None


    try:

        if "收盘" in history.columns:

            return float(
                history.iloc[-1]["收盘"]
            )


        if "close" in history.columns:

            return float(
                history.iloc[-1]["close"]
            )

    except Exception:

        return None


    return None


# =========================================================
# 4. 财务指标
# =========================================================

def get_financial_indicators(
    stock_code
):
    """
    获取财务分析指标

    主接口：
        stock_financial_analysis_indicator

    备用：
        stock_financial_analysis_indicator_em
    """

    stock_code = clean_stock_code(
        stock_code
    )

    if not stock_code:
        return None


    # -----------------------------------------------------
    # 主接口
    # -----------------------------------------------------

    symbols = [
        stock_code,
        get_symbol_code(stock_code)
    ]


    for symbol in symbols:

        try:

            data = (
                ak.stock_financial_analysis_indicator(
                    symbol=symbol
                )
            )


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

        data = (
            ak.stock_financial_analysis_indicator_em(
                symbol=stock_code,
                indicator="按报告期"
            )
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
# 5. 三大报表
# =========================================================

def get_financial_report(
    stock_code,
    report_type
):
    """
    获取财务报表

    report_type支持：
    利润表
    资产负债表
    现金流量表
    """

    stock_code = clean_stock_code(
        stock_code
    )

    if not stock_code:
        return None


    market_code = get_market_code(
        stock_code
    )


    try:

        data = (
            ak.stock_financial_report_sina(
                stock=market_code,
                symbol=report_type
            )
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
# 6. 一次获取全部基础数据
# =========================================================

def load_stock_data(
    stock_code
):
    """
    一次性加载目标股票的基础数据。

    返回：

    {
        "code": 股票代码,
        "market": 实时行情,
        "history": 历史行情,
        "indicators": 财务指标,
        "profit": 利润表,
        "balance": 资产负债表,
        "cashflow": 现金流量表
    }
    """

    stock_code = clean_stock_code(
        stock_code
    )


    if not stock_code:

        return None


    market = get_realtime_market(
        stock_code
    )


    history = get_history_data(
        stock_code
    )


    indicators = get_financial_indicators(
        stock_code
    )


    profit = get_financial_report(
        stock_code,
        "利润表"
    )


    balance = get_financial_report(
        stock_code,
        "资产负债表"
    )


    cashflow = get_financial_report(
        stock_code,
        "现金流量表"
    )


    return {

        "code":
            stock_code,

        "market":
            market,

        "history":
            history,

        "indicators":
            indicators,

        "profit":
            profit,

        "balance":
            balance,

        "cashflow":
            cashflow
    }


# =========================================================
# 7. 数据完整度检查
# =========================================================

def check_data_completeness(
    stock_data
):
    """
    检查基础数据完整程度
    """

    if stock_data is None:

        return {

            "score": 0,

            "available": 0,

            "total": 7,

            "level": "无数据"
        }


    checks = [

        stock_data.get(
            "market"
        ) is not None,

        stock_data.get(
            "history"
        ) is not None,

        stock_data.get(
            "indicators"
        ) is not None,

        stock_data.get(
            "profit"
        ) is not None,

        stock_data.get(
            "balance"
        ) is not None,

        stock_data.get(
            "cashflow"
        ) is not None,

        stock_data.get(
            "code"
        ) is not None
    ]


    available = sum(
        checks
    )

    total = len(
        checks
    )


    score = round(
        available
        / total
        * 100
    )


    if score >= 90:

        level = "优秀"


    elif score >= 75:

        level = "良好"


    elif score >= 60:

        level = "一般"


    else:

        level = "较弱"


    return {

        "score":
            score,

        "available":
            available,

        "total":
            total,

        "level":
            level
    }
