"""Claude APIの利用量（トークン数・概算コスト）を記録・集計する
(2026-07-15、14.105、Noritsuguの指定)。

Claude APIを実際に呼んでいるのは`llm_client.py`経由の3箇所だけ:
- `generate_with_tools`（chat_agent、相談機能）— ツール呼び出しの
  ラウンドごとに実際のAPI呼び出しが1回発生するため、ラウンドごとに
  1レコード記録する（feature="chat"）
- `generate_text`（資料作成のテキスト生成、帳票構造推測）
- `generate_text_with_web_search`（資料作成、Web検索付き）

`推論エンジン`(reasoning_pipeline.py)はSQL/Pythonの決定的なロジックの
みで、Claude APIを一切呼んでいないため対象外。

【重要・要確認】以下の単価は2026年1月時点の学習データに基づく参考値
であり、正確な最新料金ではない。実際の請求額とは異なる可能性がある
ため、正確な単価はdocs.claude.comで必ず確認すること（このプロジェクト
の「業務ルールを推測で決め打ちしない」方針に合わせ、断定しない）。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from services import record_store

USAGE_TABLE = "app_api_usage"

# 【要確認・参考値】Claude Sonnet系の公式料金はdocs.claude.comで確認す
# ること。ここでは学習データ時点の記憶に基づく参考値を仮置きしている。
PLACEHOLDER_INPUT_PRICE_PER_MTOK = 3.0
PLACEHOLDER_OUTPUT_PRICE_PER_MTOK = 15.0


def record_usage(feature: str, model: str, input_tokens: int, output_tokens: int) -> None:
    """1回の実際のAPI呼び出し（＝1回の`client.messages.create()`）ごとに
    記録する。永続化に失敗してもこの関数自体は例外を投げない
    （呼び出し元でtry/exceptしなくても安全 — trace_store等と同じ方針）。
    """
    try:
        record_store.append_record(USAGE_TABLE, {
            "feature": feature,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        print(f"[usage_tracking] Failed to record usage: {e}")


def _estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens / 1_000_000 * PLACEHOLDER_INPUT_PRICE_PER_MTOK
        + output_tokens / 1_000_000 * PLACEHOLDER_OUTPUT_PRICE_PER_MTOK
    )


def _bucket(records: list[dict[str, Any]], since: datetime) -> dict[str, Any]:
    matched = []
    for r in records:
        try:
            ts = datetime.fromisoformat(r["recorded_at"])
        except Exception:
            continue
        if ts >= since:
            matched.append(r)

    input_tokens = sum(r.get("input_tokens", 0) for r in matched)
    output_tokens = sum(r.get("output_tokens", 0) for r in matched)

    by_feature: dict[str, dict[str, int]] = defaultdict(
        lambda: {"input_tokens": 0, "output_tokens": 0, "calls": 0}
    )
    for r in matched:
        f = by_feature[r.get("feature", "unknown")]
        f["input_tokens"] += r.get("input_tokens", 0)
        f["output_tokens"] += r.get("output_tokens", 0)
        f["calls"] += 1

    return {
        "total_calls": len(matched),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": round(_estimate_cost_usd(input_tokens, output_tokens), 4),
        "by_feature": [
            {
                "feature": k,
                **v,
                "estimated_cost_usd": round(_estimate_cost_usd(v["input_tokens"], v["output_tokens"]), 4),
            }
            for k, v in sorted(by_feature.items(), key=lambda kv: -kv[1]["input_tokens"])
        ],
    }


def get_usage_summary() -> dict[str, Any]:
    """今日・今週(月曜始まり)・今月それぞれの合計トークン数・概算コスト・
    機能別内訳を返す。"""
    records = record_store.read_all_records(USAGE_TABLE)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    return {
        "pricing_note": (
            "単価は参考値です（要確認）。正確な最新料金はdocs.claude.comで確認してください。"
        ),
        "today": _bucket(records, today_start),
        "this_week": _bucket(records, week_start),
        "this_month": _bucket(records, month_start),
    }
