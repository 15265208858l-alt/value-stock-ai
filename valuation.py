"""
ValueStock AI
估值计算模块 V1

功能：
1. PE估值
2. PB估值
3. PE/PB综合估值
4. 建仓价
5. 重仓价
6. 高估参考价

注意：
本模块只负责“计算”，不负责获取A股数据。
"""


def calculate_pe_value(
    eps,
    target_pe
):
    """
    PE估值

    参数：
        eps: 每股收益
        target_pe: 目标PE

    返回：
        估算价格
    """

    if eps is None:
        return None

    if target_pe is None:
        return None

    if eps <= 0:
        return None

    if target_pe <= 0:
        return None

    return eps * target_pe


def calculate_pb_value(
    bvps,
    target_pb
):
    """
    PB估值

    参数：
        bvps: 每股净资产
        target_pb: 目标PB

    返回：
        估算价格
    """

    if bvps is None:
        return None

    if target_pb is None:
        return None

    if bvps <= 0:
        return None

    if target_pb <= 0:
        return None

    return bvps * target_pb


def calculate_combined_value(
    pe_value,
    pb_value,
    pe_weight=0.6,
    pb_weight=0.4
):
    """
    PE + PB 综合估值

    参数：
        pe_value: PE估值
        pb_value: PB估值
        pe_weight: PE权重
        pb_weight: PB权重

    返回：
        综合估值
    """

    # 参数检查
    if pe_weight < 0:
        return None

    if pb_weight < 0:
        return None

    total_weight = (
        pe_weight
        + pb_weight
    )

    if total_weight <= 0:
        return None

    # 自动标准化权重
    pe_weight = (
        pe_weight
        / total_weight
    )

    pb_weight = (
        pb_weight
        / total_weight
    )

    # 两者都有
    if (
        pe_value is not None
        and pb_value is not None
    ):

        return (
            pe_value * pe_weight
            + pb_value * pb_weight
        )

    # 只有PE
    if pe_value is not None:
        return pe_value

    # 只有PB
    if pb_value is not None:
        return pb_value

    return None


def calculate_price_zone(
    normal_value,
    entry_ratio=0.85,
    heavy_ratio=0.70
):
    """
    根据中性合理价值计算投资价格区间

    返回：
        {
            "entry_price": 建仓价,
            "heavy_price": 重仓价
        }
    """

    result = {
        "entry_price": None,
        "heavy_price": None
    }

    if normal_value is None:
        return result

    if normal_value <= 0:
        return result

    if entry_ratio <= 0:
        return result

    if heavy_ratio <= 0:
        return result

    result["entry_price"] = (
        normal_value
        * entry_ratio
    )

    result["heavy_price"] = (
        normal_value
        * heavy_ratio
    )

    return result


def calculate_valuation_scenarios(
    eps,
    bvps,
    conservative_pe,
    normal_pe,
    optimistic_pe,
    conservative_pb,
    normal_pb,
    optimistic_pb,
    pe_weight=0.6,
    pb_weight=0.4
):
    """
    计算保守、中性、乐观三种估值。

    返回：

    {
        "conservative": ...,
        "normal": ...,
        "optimistic": ...
    }
    """

    # PE
    pe_conservative = calculate_pe_value(
        eps,
        conservative_pe
    )

    pe_normal = calculate_pe_value(
        eps,
        normal_pe
    )

    pe_optimistic = calculate_pe_value(
        eps,
        optimistic_pe
    )

    # PB
    pb_conservative = calculate_pb_value(
        bvps,
        conservative_pb
    )

    pb_normal = calculate_pb_value(
        bvps,
        normal_pb
    )

    pb_optimistic = calculate_pb_value(
        bvps,
        optimistic_pb
    )

    # 综合
    conservative_value = (
        calculate_combined_value(
            pe_conservative,
            pb_conservative,
            pe_weight,
            pb_weight
        )
    )

    normal_value = (
        calculate_combined_value(
            pe_normal,
            pb_normal,
            pe_weight,
            pb_weight
        )
    )

    optimistic_value = (
        calculate_combined_value(
            pe_optimistic,
            pb_optimistic,
            pe_weight,
            pb_weight
        )
    )

    # 价格区间
    price_zone = calculate_price_zone(
        normal_value
    )

    return {

        "conservative": conservative_value,

        "normal": normal_value,

        "optimistic": optimistic_value,

        "entry_price": (
            price_zone["entry_price"]
        ),

        "heavy_price": (
            price_zone["heavy_price"]
        )
    }
