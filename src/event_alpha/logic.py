from __future__ import annotations

from event_alpha.sectors import DIRECTION_LABELS


def template_logic(
    *,
    summary: str,
    chain: str,
    sector: str,
    direction: str,
    data_note: str,
    trend: str | None,
    sector_l2: str | None = None,
) -> tuple[str, str]:
    sector_text = sector if not sector_l2 else f"{sector}，二级为{sector_l2}"
    logic = (
        f"{summary}。传导路径：{chain}。"
        f"适用赛道为{sector_text}，方向为{DIRECTION_LABELS[direction]}。"
        f"分数由代码按固定公式计算，数据标记为{data_note}。"
    )
    trend_text = trend or "无新闻前行业走势"
    risk = (
        "若后续信息与当前方向相反，或事件未能落地，该候选失效。"
        f"新闻前行业走势：{trend_text}。当天涨跌不作为已计价依据。"
    )
    return logic, risk
