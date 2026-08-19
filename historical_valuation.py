"""
ValueStock AI
历史估值模块 V1

功能：
1. 年度末股价
2. 年度EPS
3. 历史PE
4. 历史PE统计
5. 当前PE历史分位
"""

import pandas as pd


def safe_float(value):
    """
    安全转换数字
    """

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


def prepare_price_data(
    history
):
    """
    从历史行情中提取每年最后一个交易日价格
    """

    if (
        history is None
        or history.empty
    ):

        return pd.DataFrame()


    df = history.copy()


    if "日期" in df.columns:

        df["_日期"] = pd.to_datetime(
            df["日期"],
            errors="coerce"
        )

        df["_收盘价"] = (
            df["收盘"]
            .apply(
                safe_float
            )
        )

    elif "date" in df.columns:

        df["_日期"] = pd.to_datetime(
            df["date"],
            errors="coerce"
        )

        df["_收盘价"] = (
            df["close"]
            .apply(
                safe_float
            )
        )

    else:

        return pd.DataFrame()


    df = df.dropna(
        subset=[
            "_日期",
            "_收盘价"
        ]
    )


    if df.empty:

        return pd.DataFrame()


    df["年份"] = (
        df["_日期"]
        .dt.year
    )


    result = (
        df
        .sort_values(
            "_日期"
        )
        .groupby(
            "年份"
        )
        .tail(1)
        .copy()
    )


    return result[
        [
            "年份",
            "_日期",
            "_收盘价"
        ]
    ].rename(
        columns={
            "_日期":
                "年末日期",

            "_收盘价":
                "年末收盘价"
        }
    )


def prepare_eps_data(
    trend
):
    """
    从财务趋势中提取年度EPS
    """

    if (
        trend is None
        or trend.empty
    ):

        return pd.DataFrame()


    df = trend.copy()


    if (
        "报告期" not in df.columns
        or "EPS" not in df.columns
    ):

        return pd.DataFrame()


    df["_报告日期"] = pd.to_datetime(
        df["报告期"],
        errors="coerce"
    )


    df["EPS"] = (
        df["EPS"]
        .apply(
            safe_float
        )
    )


    df = df.dropna(
        subset=[
            "_报告日期",
            "EPS"
        ]
    )


    if df.empty:

        return pd.DataFrame()


    df["年份"] = (
        df["_报告日期"]
        .dt.year
    )


    result = (
        df
        .sort_values(
            "_报告日期"
        )
        .groupby(
            "年份"
        )
        .tail(1)
        .copy()
    )


    return result[
        [
            "年份",
            "EPS"
        ]
    ]


def build_historical_pe(
    history,
    trend,
    max_years=10
):
    """
    构建历史PE序列
    """

    price_df = prepare_price_data(
        history
    )


    eps_df = prepare_eps_data(
        trend
    )


    if (
        price_df.empty
        or eps_df.empty
    ):

        return pd.DataFrame()


    result = pd.merge(
        price_df,
        eps_df,
        on="年份",
        how="inner"
    )


    if result.empty:

        return pd.DataFrame()


    result = result[
        result["EPS"] > 0
    ].copy()


    if result.empty:

        return pd.DataFrame()


    result["PE"] = (
        result["年末收盘价"]
        / result["EPS"]
    )


    result = (
        result
        .sort_values(
            "年份"
        )
        .tail(max_years)
        .reset_index(
            drop=True
        )
    )


    return result[
        [
            "年份",
            "年末日期",
            "年末收盘价",
            "EPS",
            "PE"
        ]
    ]


def calculate_historical_statistics(
    historical_pe,
    current_pe
):
    """
    计算历史PE统计数据
    """

    if (
        historical_pe is None
        or historical_pe.empty
    ):

        return {

            "min": None,

            "q25": None,

            "median": None,

            "q75": None,

            "max": None,

            "percentile": None,

            "deviation": None
        }


    pe_values = (
        historical_pe[
            "PE"
        ]
        .dropna()
        .astype(float)
        .tolist()
    )


    if not pe_values:

        return {

            "min": None,

            "q25": None,

            "median": None,

            "q75": None,

            "max": None,

            "percentile": None,

            "deviation": None
        }


    series = pd.Series(
        pe_values
    )


    minimum = (
        series.min()
    )


    q25 = (
        series.quantile(
            0.25
        )
    )


    median = (
        series.median()
    )


    q75 = (
        series.quantile(
            0.75
        )
    )


    maximum = (
        series.max()
    )


    percentile = None


    if current_pe is not None:

        lower_count = sum(
            1
            for value
            in pe_values
            if value <= current_pe
        )


        percentile = (
            lower_count
            / len(pe_values)
            * 100
        )


    deviation = None


    if (
        current_pe is not None
        and median is not None
        and median > 0
    ):

        deviation = (
            current_pe
            / median
            - 1
        ) * 100


    return {

        "min": minimum,

        "q25": q25,

        "median": median,

        "q75": q75,

        "max": maximum,

        "percentile": percentile,

        "deviation": deviation
    }


def get_historical_valuation_level(
    percentile
):
    """
    根据历史分位判断估值区域
    """

    if percentile is None:

        return "数据不足"


    if percentile <= 20:

        return "历史低位"


    if percentile <= 40:

        return "历史中低位"


    if percentile <= 60:

        return "历史中枢"


    if percentile <= 80:

        return "历史中高位"


    return "历史高位"
