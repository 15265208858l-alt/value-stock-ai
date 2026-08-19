"""
ValueStock AI
财务分析模块

负责：
1. 财务指标字段识别
2. 最新报告期处理
3. 最近完整年度处理
4. 5年趋势处理
5. 财务质量评分
"""


import pandas as pd


def safe_float(value):
    """安全转换数字"""

    try:

        if value is None:
            return None

        text = str(value).strip()

        if text in [
            "",
            "--",
            "None",
            "none",
            "NaN",
            "nan"
        ]:
            return None

        text = text.replace(
            ",",
            ""
        )

        text = text.replace(
            "%",
            ""
        )

        return float(text)

    except Exception:

        return None


def find_column(
    df,
    candidates
):
    """寻找字段"""

    if (
        df is None
        or df.empty
    ):
        return None

    for column in candidates:

        if column in df.columns:

            return column

    return None


def parse_date_column(df):
    """识别报告期"""

    if (
        df is None
        or df.empty
    ):

        return (
            df,
            None
        )

    date_col = find_column(
        df,
        [
            "日期",
            "报告期",
            "报告日期",
            "截止日期",
            "REPORT_DATE"
        ]
    )

    if date_col is None:

        return (
            df.copy(),
            None
        )

    result = df.copy()

    result["_分析日期"] = (
        pd.to_datetime(
            result[date_col],
            errors="coerce"
        )
    )

    result = (
        result
        .dropna(
            subset=[
                "_分析日期"
            ]
        )
        .sort_values(
            "_分析日期",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )

    if result.empty:

        return (
            df.copy(),
            date_col
        )

    return (
        result,
        date_col
    )


def get_indicator_columns(
    df
):
    """获取关键财务指标字段"""

    return {

        "roe": find_column(
            df,
            [
                "加权净资产收益率(%)",
                "加权净资产收益率",
                "摊薄净资产收益率(%)",
                "摊薄净资产收益率",
                "净资产收益率(%)",
                "净资产收益率",
                "ROEJQ"
            ]
        ),

        "revenue_growth": find_column(
            df,
            [
                "主营业务收入增长率(%)",
                "主营业务收入增长率",
                "营业收入增长率(%)",
                "营业收入增长率",
                "TOTALOPERATEREVETZ"
            ]
        ),

        "profit_growth": find_column(
            df,
            [
                "净利润增长率(%)",
                "净利润增长率",
                "归属净利润同比增长(%)",
                "PARENTNETPROFITTZ"
            ]
        ),

        "debt": find_column(
            df,
            [
                "资产负债率(%)",
                "资产负债率",
                "ZCFZL"
            ]
        ),

        "eps": find_column(
            df,
            [
                "摊薄每股收益(元)",
                "摊薄每股收益",
                "基本每股收益(元)",
                "基本每股收益",
                "每股收益(元)",
                "每股收益",
                "EPSJB"
            ]
        ),

        "bvps": find_column(
            df,
            [
                "每股净资产(元)",
                "每股净资产",
                "每股净资产_调整后(元)",
                "归属母公司股东的每股净资产",
                "BPS"
            ]
        )
    }


def process_financial_indicators(
    indicators
):
    """
    将原始财务指标整理成：
    latest / annual / trend
    """

    result = {

        "latest": {},

        "annual": {},

        "trend":
            pd.DataFrame()
    }


    if (
        indicators is None
        or indicators.empty
    ):

        return result


    df, date_col = (
        parse_date_column(
            indicators
        )
    )


    if (
        df is None
        or df.empty
    ):

        return result


    columns = (
        get_indicator_columns(
            df
        )
    )


    # =====================================================
    # 最新报告期
    # =====================================================

    latest = df.iloc[0]


    result["latest"] = {

        "roe":
            safe_float(
                latest[
                    columns["roe"]
                ]
            )
            if columns["roe"]
            else None,

        "revenue_growth":
            safe_float(
                latest[
                    columns[
                        "revenue_growth"
                    ]
                ]
            )
            if columns[
                "revenue_growth"
            ]
            else None,

        "profit_growth":
            safe_float(
                latest[
                    columns[
                        "profit_growth"
                    ]
                ]
            )
            if columns[
                "profit_growth"
            ]
            else None,

        "debt":
            safe_float(
                latest[
                    columns["debt"]
                ]
            )
            if columns["debt"]
            else None,

        "eps":
            safe_float(
                latest[
                    columns["eps"]
                ]
            )
            if columns["eps"]
            else None,

        "bvps":
            safe_float(
                latest[
                    columns["bvps"]
                ]
            )
            if columns["bvps"]
            else None
    }


    # =====================================================
    # 最近完整年度
    # =====================================================

    annual_df = pd.DataFrame()


    if "_分析日期" in df.columns:

        annual_df = df[
            df[
                "_分析日期"
            ].dt.month == 12
        ].copy()


    if annual_df.empty:

        annual = latest

    else:

        annual = (
            annual_df
            .sort_values(
                "_分析日期"
            )
            .iloc[-1]
        )


    result["annual"] = {

        "roe":
            safe_float(
                annual[
                    columns["roe"]
                ]
            )
            if columns["roe"]
            else None,

        "revenue_growth":
            safe_float(
                annual[
                    columns[
                        "revenue_growth"
                    ]
                ]
            )
            if columns[
                "revenue_growth"
            ]
            else None,

        "profit_growth":
            safe_float(
                annual[
                    columns[
                        "profit_growth"
                    ]
                ]
            )
            if columns[
                "profit_growth"
            ]
            else None,

        "debt":
            safe_float(
                annual[
                    columns["debt"]
                ]
            )
            if columns["debt"]
            else None,

        "eps":
            safe_float(
                annual[
                    columns["eps"]
                ]
            )
            if columns["eps"]
            else None,

        "bvps":
            safe_float(
                annual[
                    columns["bvps"]
                ]
            )
            if columns["bvps"]
            else None
    }


    # =====================================================
    # 5年趋势
    # =====================================================

    trend = df.copy()


    if "_分析日期" in trend.columns:

        trend["年份"] = (
            trend[
                "_分析日期"
            ].dt.year
        )


        annual_trend = trend[
            trend[
                "_分析日期"
            ].dt.month == 12
        ].copy()


        if not annual_trend.empty:

            trend = (
                annual_trend
                .sort_values(
                    "_分析日期"
                )
                .groupby(
                    "年份"
                )
                .tail(1)
                .tail(5)
            )

        else:

            trend = (
                trend
                .sort_values(
                    "_分析日期"
                )
                .tail(5)
            )


    rename_map = {}


    if date_col:

        rename_map[
            date_col
        ] = "报告期"


    if columns["roe"]:

        rename_map[
            columns["roe"]
        ] = "ROE"


    if columns[
        "revenue_growth"
    ]:

        rename_map[
            columns[
                "revenue_growth"
            ]
        ] = "营收增长率"


    if columns[
        "profit_growth"
    ]:

        rename_map[
            columns[
                "profit_growth"
            ]
        ] = "净利润增长率"


    if columns["debt"]:

        rename_map[
            columns["debt"]
        ] = "资产负债率"


    if columns["eps"]:

        rename_map[
            columns["eps"]
        ] = "EPS"


    trend = trend.rename(
        columns=rename_map
    )


    display_columns = []


    for column in [
        "报告期",
        "ROE",
        "营收增长率",
        "净利润增长率",
        "资产负债率",
        "EPS"
    ]:

        if column in trend.columns:

            display_columns.append(
                column
            )


    if display_columns:

        result["trend"] = (
            trend[
                display_columns
            ].copy()
        )


    return result


def calculate_financial_quality(
    trend,
    cash_profit_ratio=None
):
    """
    计算财务质量评分
    满分100
    """

    roe_values = []

    revenue_values = []

    profit_values = []

    debt_values = []


    if (
        trend is not None
        and not trend.empty
    ):

        if "ROE" in trend.columns:

            for value in trend[
                "ROE"
            ]:

                number = safe_float(
                    value
                )

                if number is not None:

                    roe_values.append(
                        number
                    )


        if "营收增长率" in trend.columns:

            for value in trend[
                "营收增长率"
            ]:

                number = safe_float(
                    value
                )

                if number is not None:

                    revenue_values.append(
                        number
                    )


        if "净利润增长率" in trend.columns:

            for value in trend[
                "净利润增长率"
            ]:

                number = safe_float(
                    value
                )

                if number is not None:

                    profit_values.append(
                        number
                    )


        if "资产负债率" in trend.columns:

            for value in trend[
                "资产负债率"
            ]:

                number = safe_float(
                    value
                )

                if number is not None:

                    debt_values.append(
                        number
                    )


    roe_score = 0

    growth_score = 0

    profit_score = 0

    debt_score = 0

    cash_score = 0


    # =====================================================
    # ROE 20分
    # =====================================================

    if roe_values:

        avg_roe = (
            sum(roe_values)
            / len(roe_values)
        )

        min_roe = min(
            roe_values
        )


        if (
            avg_roe >= 20
            and min_roe >= 15
        ):

            roe_score = 20


        elif (
            avg_roe >= 15
            and min_roe >= 10
        ):

            roe_score = 17


        elif avg_roe >= 10:

            roe_score = 13


        elif avg_roe >= 5:

            roe_score = 8


        else:

            roe_score = 3


    # =====================================================
    # 营收成长 20分
    # =====================================================

    if revenue_values:

        avg_growth = (
            sum(revenue_values)
            / len(revenue_values)
        )

        positive_years = sum(
            1
            for x in revenue_values
            if x >= 0
        )


        if (
            avg_growth >= 15
            and positive_years >= 4
        ):

            growth_score = 20


        elif (
            avg_growth >= 8
            and positive_years >= 4
        ):

            growth_score = 16


        elif avg_growth >= 0:

            growth_score = 11


        else:

            growth_score = 4


    # =====================================================
    # 净利润成长 20分
    # =====================================================

    if profit_values:

        avg_profit_growth = (
            sum(profit_values)
            / len(profit_values)
        )

        positive_profit_years = sum(
            1
            for x in profit_values
            if x >= 0
        )


        if (
            avg_profit_growth >= 20
            and positive_profit_years >= 4
        ):

            profit_score = 20


        elif (
            avg_profit_growth >= 10
            and positive_profit_years >= 4
        ):

            profit_score = 16


        elif avg_profit_growth >= 0:

            profit_score = 11


        else:

            profit_score = 4


    # =====================================================
    # 财务安全 20分
    # =====================================================

    if debt_values:

        avg_debt = (
            sum(debt_values)
            / len(debt_values)
        )


        if avg_debt < 50:

            debt_score = 20


        elif avg_debt < 60:

            debt_score = 17


        elif avg_debt < 70:

            debt_score = 13


        elif avg_debt < 80:

            debt_score = 8


        else:

            debt_score = 3


    # =====================================================
    # 现金流 20分
    # =====================================================

    if cash_profit_ratio is not None:

        if cash_profit_ratio >= 1:

            cash_score = 20


        elif cash_profit_ratio >= 0.7:

            cash_score = 16


        elif cash_profit_ratio >= 0:

            cash_score = 10


        else:

            cash_score = 3


    total_score = min(
        100,
        (
            roe_score
            + growth_score
            + profit_score
            + debt_score
            + cash_score
        )
    )


    if total_score >= 85:

        rating = "优秀"


    elif total_score >= 75:

        rating = "良好"


    elif total_score >= 60:

        rating = "一般"


    else:

        rating = "偏弱"


    return {

        "score": total_score,

        "rating": rating,

        "roe_score": roe_score,

        "growth_score": growth_score,

        "profit_score": profit_score,

        "debt_score": debt_score,

        "cash_score": cash_score
    }
