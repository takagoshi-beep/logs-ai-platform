"use client";

import { useEffect, useState } from "react";
import { Card, EmptyState, SectionHeader, StatusBadge } from "@/components/design-system";
import { getExecutionHistory } from "@/lib/api-client";

interface HistoryItem {
  type: "capability_execution" | "governance_approval";
  id: string;
  status: string;
  timestamp: string;
  trace_id: string;
  capability_id?: string;
  concept?: string;
}

const STATUS_LABEL: Record<string, string> = {
  completed: "完了",
  failed: "失敗",
  running: "実行中",
  QUEUED_FOR_REVIEW: "承認待ち",
  APPROVED: "承認済み",
  REJECTED: "却下",
};

function itemTitle(item: HistoryItem): string {
  if (item.type === "governance_approval") {
    return item.concept || item.id;
  }
  return item.capability_id || item.id;
}

function itemTypeLabel(item: HistoryItem): string {
  return item.type === "governance_approval" ? "Governance承認" : "AI機能の実行";
}

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleString("ja-JP");
  } catch {
    return ts;
  }
}

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getExecutionHistory()
      .then((data: any) => {
        if (data?.success === false) {
          setError(data.error ?? "履歴の取得に失敗しました");
          return;
        }
        setItems(data?.items ?? []);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">履歴</h1>
        <p className="page-subtitle">
          AI機能の実行記録と、Governanceでの承認・却下の履歴です（実データ）。
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          {error}
        </div>
      )}

      <Card>
        <SectionHeader title="実行・承認履歴" subtitle="新しい順に表示しています。" />
        {loading && <p className="py-8 text-center text-sm text-sub">読み込み中...</p>}
        {!loading && items.length === 0 && (
          <p className="py-8 text-center text-sm text-sub">まだ履歴がありません</p>
        )}
        {!loading && items.length > 0 && (
          <ul className="space-y-2 text-sm">
            {items.map((item) => (
              <li key={`${item.type}-${item.id}`} className="surface-soft p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-medium text-ink">{itemTitle(item)}</div>
                  <StatusBadge status={STATUS_LABEL[item.status] ?? item.status} />
                </div>
                <div className="text-xs text-sub">
                  {itemTypeLabel(item)} | {formatTimestamp(item.timestamp)}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <EmptyState
        title="フィードバックキュー（V0.2予定）"
        description="生成結果への承認・却下・修正フィードバックを送信できる機能は、次バージョンで提供予定です。"
      />
    </div>
  );
}
