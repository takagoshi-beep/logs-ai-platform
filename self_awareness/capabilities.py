from __future__ import annotations

from typing import Any

from learning.improvements import list_improvements
from system.logic_registry import get_logic_registry


def get_capabilities() -> dict[str, Any]:
    logic_registry = get_logic_registry()
    return {
        "business": [
            "売上要約",
            "売上ランキング",
            "商品検索",
            "顧客一覧・詳細取得",
        ],
        "knowledge": [
            "業務用語の説明",
            "会社情報の参照",
            "ブランド情報の参照",
        ],
        "system": [
            "ロジックレジストリの参照",
            "システムマップの参照",
        ],
        "workflow": [
            "Planner結果からWorkflow生成",
            "順次実行管理",
        ],
        "answer": [
            "結果の自然な文章化",
            "複数セクションの整形",
        ],
        "learning": [
            "質問ログ保存",
            "フィードバック保存",
            "改善管理",
        ],
        "logic_count": len(logic_registry),
    }


def get_limitations() -> list[dict[str, Any]]:
    return [
        {"area": "粗利分析", "reason": "現在の業務ロジックには粗利計算の専用処理がありません。"},
        {"area": "在庫分析", "reason": "在庫データの取得・集計フローは未実装です。"},
        {"area": "需要予測", "reason": "将来予測や時系列分析は未実装です。"},
        {"area": "営業担当別分析", "reason": "担当者単位の分析ロジックは未実装です。"},
    ]


def get_next_recommendations() -> list[dict[str, Any]]:
    improvements = list_improvements()
    recommendations = []
    for item in improvements[:5]:
        recommendations.append(
            {
                "improvement_id": item.get("improvement_id"),
                "title": item.get("title"),
                "priority": item.get("priority"),
                "status": item.get("status"),
            }
        )
    if not recommendations:
        recommendations.append({"title": "粗利分析ロジックの追加", "priority": "high", "status": "open"})
    return recommendations
