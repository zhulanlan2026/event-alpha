from __future__ import annotations

import json
from pathlib import Path

from event_alpha.handoff import factor_record
from event_alpha.models import FactorCard


class FactorLibrary:
    """候选库只供初筛去重。解析提示词不读取这里的记录。"""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.candidates_path = self.directory / "candidates.jsonl"
        self.processed_path = self.directory / "processed.jsonl"

    def news_done(self, news_id: str) -> bool:
        return any(
            row.get("news_id") == news_id and row.get("scope") == "news"
            for row in self._rows(self.processed_path)
        )

    def pair_done(self, news_id: str, sector: str) -> bool:
        return any(
            row.get("news_id") == news_id
            and row.get("sector") == sector
            and row.get("scope") == "card"
            for row in self._rows(self.processed_path)
        )

    def append_candidate(self, card: FactorCard) -> None:
        self._append(self.candidates_path, card.to_public_dict())
        factor_dir = self.directory / "factors"
        factor_dir.mkdir(parents=True, exist_ok=True)
        path = factor_dir / f"{card.factor_name}.json"
        path.write_text(json.dumps(factor_record(card), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def mark_card(self, news_id: str, sector: str, reject_reason: str | None, factor_name: str) -> None:
        self._append(
            self.processed_path,
            {
                "scope": "card",
                "news_id": news_id,
                "sector": sector,
                "reject_reason": reject_reason,
                "factor_name": factor_name,
            },
        )

    def mark_news(self, news_id: str) -> None:
        self._append(self.processed_path, {"scope": "news", "news_id": news_id})

    def candidate_count(self) -> int:
        return len(self._rows(self.candidates_path))

    def _append(self, path: Path, payload: dict) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _rows(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
