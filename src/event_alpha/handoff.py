"""交给中游的因子定义。上游不做中性化、IC 和回测。"""

VALUE_RULE = (
    "有效期内，申万一级成份股的因子值等于 signed_score；有效期外为 0。"
    "同一一级行业内分数相同，用于检验行业方向。"
    "sector_l2 有值时，in_level2 为真的成份股是一级内部的对照子集，分数仍与一级相同。"
)


def factor_record(card) -> dict:
    return {
        "名称": card.factor_name,
        "逻辑": card.factor_logic,
        "表达式": card.factor_expr,
        "适用赛道": card.sector,
        "二级行业": card.sector_l2,
        "持仓周期": card.holding_period,
        "新闻时间": card.news_time,
        "有效期截止": card.valid_until,
        "方向": card.direction,
        "带符号分数": card.signed_score,
        "数据标记": card.data_note,
        "赋值规则": card.value_rule,
        "成份说明": card.constituent_note,
        "成份口径": card.constituent_basis,
        "成份股": card.constituents,
        "结果类型": card.result_kind,
        "状态": card.status,
    }
