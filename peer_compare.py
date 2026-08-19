"""
ValueStock AI
同行业比较模块 V1

功能：
1. 多家公司核心财务指标横向比较
2. 行业平均值
3. ROE排名
4. 成长性排名
5. PE/PB比较
6. 资产负债率比较
7. 同行竞争力评分
"""


import pandas as pd


def safe_rank_score(
    rank,
    total,
    max_score
):
    """
    根据排名计算得分
    """

    if rank is None:
        return 0

    if total <= 1:
        return max_score

    if rank == 1:
        return max_score

    if rank == 2:
        return max_score * 0.85

    if rank == 3:
        return max_score * 0.70

    if rank <= max(4, total // 2):
        return max_score * 0.50

    return max_score * 0.25


def calculate_peer_rank(
    df,
    column,
    ascending=False
):
    """
    计算某项指标排名
    """

    if (
        df is None
        or df.empty
        or column not in df.columns
    ):

        return None


    valid = (
        df[
            [
                "代码",
                column
            ]
        ]
        .dropna(
            subset=[
                column
            ]
        )
        .copy()
    )


    if valid.empty:
        return None


    valid["_排名"] = (
        valid[column]
        .rank(
            ascending=ascending,
            method="min"
        )
    )


    return valid


def calculate_peer_score(
    df,
    target_code
):
    """
    计算目标公司的同行竞争力评分
    """

    if (
        df is None
        or df.empty
        or target_code not in
        df["代码"].values
    ):

        return {
            "score": 0,
            "rating": "数据不足",
            "details": []
        }


    target = df[
        df["代码"] == target_code
    ].iloc[0]


    total_score = 0

    details = []


    # =====================================================
    # ROE：30分
    # =====================================================

    roe_rank_df = calculate_peer_rank(
        df,
        "ROE",
        ascending=False
    )


    if roe_rank_df is not None:

        target_row = roe_rank_df[
            roe_rank_df["代码"]
            == target_code
        ]


        if not target_row.empty:

            rank = int(
                target_row[
                    "_排名"
                ].iloc[0]
            )


            score = safe_rank_score(
                rank,
                len(roe_rank_df),
                30
            )


            total_score += score


            details.append({
                "指标": "ROE",
                "排名": rank,
                "得分": round(
                    score,
                    1
                )
            })


    # =====================================================
    # 营收增长：20分
    # =====================================================

    revenue_rank_df = calculate_peer_rank(
        df,
        "营收增长率",
        ascending=False
    )


    if revenue_rank_df is not None:

        target_row = revenue_rank_df[
            revenue_rank_df["代码"]
            == target_code
        ]


        if not target_row.empty:

            rank = int(
                target_row[
                    "_排名"
                ].iloc[0]
            )


            score = safe_rank_score(
                rank,
                len(revenue_rank_df),
                20
            )


            total_score += score


            details.append({
                "指标": "营收增长率",
                "排名": rank,
                "得分": round(
                    score,
                    1
                )
            })


    # =====================================================
    # 净利润增长：20分
    # =====================================================

    profit_rank_df = calculate_peer_rank(
        df,
        "净利润增长率",
        ascending=False
    )


    if profit_rank_df is not None:

        target_row = profit_rank_df[
            profit_rank_df["代码"]
            == target_code
        ]


        if not target_row.empty:

            rank = int(
                target_row[
                    "_排名"
                ].iloc[0]
            )


            score = safe_rank_score(
                rank,
                len(profit_rank_df),
                20
            )


            total_score += score


            details.append({
                "指标": "净利润增长率",
                "排名": rank,
                "得分": round(
                    score,
                    1
                )
            })


    # =====================================================
    # PE：15分
    # PE越低越优
    # =====================================================

    pe_rank_df = calculate_peer_rank(
        df,
        "PE",
        ascending=True
    )


    if pe_rank_df is not None:

        target_row = pe_rank_df[
            pe_rank_df["代码"]
            == target_code
        ]


        if not target_row.empty:

            rank = int(
                target_row[
                    "_排名"
                ].iloc[0]
            )


            score = safe_rank_score(
                rank,
                len(pe_rank_df),
                15
            )


            total_score += score


            details.append({
                "指标": "PE",
                "排名": rank,
                "得分": round(
                    score,
                    1
                )
            })


    # =====================================================
    # 资产负债率：15分
    # 越低越优
    # =====================================================

    debt_rank_df = calculate_peer_rank(
        df,
        "资产负债率",
        ascending=True
    )


    if debt_rank_df is not None:

        target_row = debt_rank_df[
            debt_rank_df["代码"]
            == target_code
        ]


        if not target_row.empty:

            rank = int(
                target_row[
                    "_排名"
                ].iloc[0]
            )


            score = safe_rank_score(
                rank,
                len(debt_rank_df),
                15
            )


            total_score += score


            details.append({
                "指标": "资产负债率",
                "排名": rank,
                "得分": round(
                    score,
                    1
                )
            })


    total_score = round(
        total_score
    )


    if total_score >= 85:

        rating = "优秀"

    elif total_score >= 70:

        rating = "良好"

    elif total_score >= 55:

        rating = "一般"

    else:

        rating = "偏弱"


    return {

        "score": total_score,

        "rating": rating,

        "details": details
    }


def build_peer_summary(
    df
):
    """
    计算同行平均值
    """

    if (
        df is None
        or df.empty
    ):

        return pd.DataFrame()


    columns = [

        "ROE",

        "营收增长率",

        "净利润增长率",

        "资产负债率",

        "PE",

        "PB"

    ]


    available = [

        column

        for column in columns

        if column in df.columns

    ]


    if not available:

        return pd.DataFrame()


    summary = []


    for column in available:

        summary.append({

            "指标": column,

            "同行平均":

                df[column]
                .mean()

        })


    result = pd.DataFrame(
        summary
    )


    result[
        "同行平均"
    ] = (
        result[
            "同行平均"
        ]
        .round(2)
    )


    return result


def compare_target_with_average(
    df,
    target_code
):
    """
    目标公司与同行平均比较
    """

    result = []


    if (
        df is None
        or df.empty
    ):

        return result


    target_rows = df[
        df["代码"]
        == target_code
    ]


    if target_rows.empty:

        return result


    target = (
        target_rows
        .iloc[0]
    )


    metrics = [

        (
            "ROE",
            "higher_better"
        ),

        (
            "营收增长率",
            "higher_better"
        ),

        (
            "净利润增长率",
            "higher_better"
        ),

        (
            "资产负债率",
            "lower_better"
        ),

        (
            "PE",
            "lower_better"
        ),

        (
            "PB",
            "lower_better"
        )
    ]


    for metric, direction in metrics:

        if metric not in df.columns:

            continue


        target_value = target[
            metric
        ]


        average_value = (
            df[metric]
            .mean()
        )


        if pd.isna(
            target_value
        ):

            continue


        if direction == "higher_better":

            if target_value > average_value:

                judgment = "高于同行"

            elif target_value < average_value:

                judgment = "低于同行"

            else:

                judgment = "接近同行"

        else:

            if target_value < average_value:

                judgment = "优于同行"

            elif target_value > average_value:

                judgment = "弱于同行"

            else:

                judgment = "接近同行"


        result.append({

            "指标": metric,

            "目标公司": round(
                float(
                    target_value
                ),
                2
            ),

            "同行平均": round(
                float(
                    average_value
                ),
                2
            ),

            "判断": judgment
        })


    return result
