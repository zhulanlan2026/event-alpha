from __future__ import annotations

import json
import os
import urllib.request

from event_alpha.models import ParsedEvent, SectorImpact
from event_alpha.sectors import (
    DIRECTIONS,
    EVENT_TYPES,
    HORIZONS,
    MAGNITUDES,
    SW_INDUSTRIES,
)

PARSE_PROMPT = """你是量化事件投研分析师。把输入新闻拆成结构化 JSON，供事件 Alpha 候选因子使用。
规则：
1. 输出升到赛道。输出里不写公司名，不写证券代码，不写「股份」和「有限公司」。
2. 只写事件带来的预期差。不写市值、行业贝塔、估值和财报静态比较。
3. sector 只能取给定的申万一级名单。
4. event_type 只能是 policy、supply、tech、overseas、macro。
5. 每个赛道单独给 direction：positive、negative、neutral。
6. magnitude_bucket 只根据新闻内容判断：weak、mid、strong。
7. horizon 只能是 short_1_5 或 mid_5_20。
输出字段：event_summary，impact_chain，event_type，magnitude_bucket，signal_confidence，has_alpha_potential，items。
items 的元素为 sector、direction、horizon。只输出 JSON。
申万一级名单：{sectors}
"""

LOGIC_PROMPT = """你根据已经给定的结构化字段写两段中文：factor_logic 和 risk_note。
不得改写方向、分数、偏离和赛道。不得提出买卖建议，不得预测涨跌。
risk_note 说明失效条件、拥挤可能，以及调用方提供的新闻前行业走势。
调用方没有 consensus_surprise 时，不得使用「超预期」三个字。
只输出 JSON：{"factor_logic": "...", "risk_note": "..."}
"""


def parsed_event_from_dict(payload: dict) -> ParsedEvent:
    items = [
        SectorImpact(
            sector=str(item["sector"]),
            direction=str(item["direction"]),
            horizon=str(item["horizon"]),
        )
        for item in payload.get("items") or []
    ]
    return ParsedEvent(
        event_summary=str(payload.get("event_summary") or ""),
        impact_chain=str(payload.get("impact_chain") or ""),
        event_type=str(payload.get("event_type") or ""),
        magnitude_bucket=str(payload.get("magnitude_bucket") or ""),
        signal_confidence=float(payload.get("signal_confidence")),
        has_alpha_potential=bool(payload.get("has_alpha_potential")),
        items=items,
    )


def extract_json(text: str) -> dict:
    body = text.strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[1]
        body = body.rsplit("```", 1)[0]
    start = body.find("{")
    end = body.rfind("}")
    if start < 0 or end < start:
        raise ValueError("模型输出里没有 JSON")
    return json.loads(body[start : end + 1])


def _event(
    summary: str,
    chain: str,
    event_type: str,
    magnitude: str,
    confidence: float,
    has_alpha: bool,
    sector: str,
    direction: str,
    horizon: str,
) -> ParsedEvent:
    return ParsedEvent(
        event_summary=summary,
        impact_chain=chain,
        event_type=event_type,
        magnitude_bucket=magnitude,
        signal_confidence=confidence,
        has_alpha_potential=has_alpha,
        items=[SectorImpact(sector, direction, horizon)],
    )


FIXTURE_EVENTS = {
    "国家级产业规划明确加大对电力设备的购置补贴。": _event(
        "国家级规划加大对电力设备的购置补贴",
        "补贴提高下游资本开支，电力设备订单预期改善",
        "policy",
        "strong",
        0.80,
        True,
        "电力设备",
        "positive",
        "mid_5_20",
    ),
    "国内主要铜冶炼企业宣布联合减产。": _event(
        "铜冶炼环节宣布联合减产",
        "冶炼减产收紧精炼铜供给，有色金属价格弹性上升",
        "supply",
        "strong",
        0.80,
        True,
        "有色金属",
        "positive",
        "short_1_5",
    ),
    "某股份公司股东拟减持不超过 2% 股份。": _event(
        "单一股东减持，没有赛道级供需变化",
        "影响停留在个别主体，不向行业扩散",
        "policy",
        "weak",
        0.20,
        False,
        "综合",
        "neutral",
        "short_1_5",
    ),
    "国家统计局公布制造业 PMI 为 49.3。": _event(
        "制造业PMI公布值为49.3",
        "制造业景气读数偏弱，机械设备订单预期承压",
        "macro",
        "mid",
        0.75,
        True,
        "机械设备",
        "negative",
        "short_1_5",
    ),
}


class FixtureParser:
    """没有密钥时，只识别仓库里的四条自制短句。"""

    def parse(self, content: str) -> ParsedEvent | None:
        return FIXTURE_EVENTS.get(content.strip())


class DeepSeekParser:
    def __init__(self, api_key: str, transport=None, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.transport = transport or _urllib_chat
        self.model = model

    def parse(self, content: str) -> ParsedEvent | None:
        prompt = PARSE_PROMPT.format(sectors="、".join(SW_INDUSTRIES))
        text = self.transport(
            api_key=self.api_key,
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content},
            ],
        )
        return parsed_event_from_dict(extract_json(text))

    def write_logic(self, payload: dict) -> tuple[str, str]:
        text = self.transport(
            api_key=self.api_key,
            model=self.model,
            messages=[
                {"role": "system", "content": LOGIC_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        data = extract_json(text)
        return str(data["factor_logic"]), str(data["risk_note"])


def _urllib_chat(*, api_key: str, model: str, messages: list[dict]) -> str:
    body = json.dumps({"model": model, "messages": messages, "temperature": 0}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def parser_from_env():
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        return None
    return DeepSeekParser(key)


def enums_ok(event_type: str, direction: str, horizon: str, magnitude: str, sector: str) -> dict[str, bool]:
    return {
        "allowed_event": event_type in EVENT_TYPES,
        "allowed_direction": direction in DIRECTIONS,
        "allowed_horizon": horizon in HORIZONS,
        "allowed_magnitude": magnitude in MAGNITUDES,
        "allowed_sector": sector in SW_INDUSTRIES,
    }
