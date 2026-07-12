"use client";

import { useEffect, useState } from "react";
import { Card, EmptyState, SectionHeader, StatusBadge } from "@/components/design-system";
import { getExecutionHistory, getExecution } from "@/lib/api-client";

interface HistoryItem {
  type: "capability_execution" | "governance_approval";
  id: string;
  status: string;
  timestamp: string;
  trace_id: string;
  capability_id?: string;
  concept?: string;
}

interface ExecutionDetail {
  execution_id: string;
  capability_id?: string;
  capability_version?: string;
  project_id?: string;
  user_id?: string;
  trace_id?: string;
  status: string;
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown>;
  started_at?: string | null;
  completed_at?: string | null;
  execution_time_seconds?: number;
  error_message?: string | null;
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

  // 2026-07-14（14.101、Noritsuguの指定）: 各行は元々executionのidを
  // 持っていたが、クリックしても何も起きなかった（GET /api/executions/{id}
  // は実装済みで実データを返すが、フロントエンドから未接続だった）。
  // 行クリックで詳細（入力・出力・エラー内容）を展開表示するようにした。
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detailCache, setDetailCache] = useState<Record<string, ExecutionDetail>>({});
  const [detailLoading, setDetailLoading] = useState<string | null>(null);

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

  function handleRowClick(item: HistoryItem) {
    // Governance承認の履歴には対応するCapability実行詳細が無いため
    // （getExecutionはcapability_executionのIDしか探さない）、展開対象外。
    if (item.type !== "capability_execution") return;

    if (expandedId === item.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(item.id);
    if (!detailCache[item.id]) {
      setDetailLoading(item.id);
      getExecution(item.id)
        .then((data: any) => {
          setDetailCache((prev) => ({ ...prev, [item.id]: data }));
        })
        .finally(() => setDetailLoading(null));
    }
  }

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
        <SectionHeader title="実行・承認履歴" subtitle="新しい順に表示しています。AI機能の実行はクリックすると詳細が見られます。" />
        {loading && <p className="py-8 text-center text-sm text-sub">読み込み中...</p>}
        {!loading && items.length === 0 && (
          <p className="py-8 text-center text-sm text-sub">まだ履歴がありません</p>
        )}
        {!loading && items.length > 0 && (
          <ul className="space-y-2 text-sm">
            {items.map((item) => {
              const isExpanded = expandedId === item.id;
              const detail = detailCache[item.id];
              const clickable = item.type === "capability_execution";
              return (
                <li key={`${item.type}-${item.id}`} className="surface-soft p-3">
                  <div
                    className={`flex items-center justify-between gap-2 ${clickable ? "cursor-pointer" : ""}`}
                    onClick={() => handleRowClick(item)}
                  >
                    <div className="font-medium text-ink">{itemTitle(item)}</div>
                    <StatusBadge status={STATUS_LABEL[item.status] ?? item.status} />
                  </div>
                  <div className="text-xs text-sub">
                    {itemTypeLabel(item)} | {formatTimestamp(item.timestamp)}
                  </div>

                  {isExpanded && (
                    <div className="mt-2 rounded-lg border border-slate-200 bg-white p-3 text-xs">
                      {detailLoading === item.id && <p className="text-sub">詳細を読み込み中...</p>}
                      {detail && detail.status === "not_found" && (
                        <p className="text-sub">詳細データが見つかりませんでした。</p>
                      )}
                      {detail && detail.status !== "not_found" && (
                        <div className="space-y-1">
                          <div>trace_id: {detail.trace_id ?? "—"}</div>
                          <div>project_id: {detail.project_id ?? "—"}</div>
                          <div>実行時間: {detail.execution_time_seconds != null ? `${detail.execution_time_seconds.toFixed(2)}秒` : "—"}</div>
                          <div>開始: {detail.started_at ? formatTimestamp(detail.started_at) : "—"}</div>
                          <div>終了: {detail.completed_at ? formatTimestamp(detail.completed_at) : "—"}</div>
                          {detail.error_message && (
                            <div className="text-red-600">エラー: {detail.error_message}</div>
                          )}
                          <div className="mt-1">
                            <div className="font-medium">入力</div>
                            <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2">{JSON.stringify(detail.inputs ?? {}, null, 2)}</pre>
                          </div>
                          <div className="mt-1">
                            <div className="font-medium">出力</div>
                            <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2">{JSON.stringify(detail.outputs ?? {}, null, 2)}</pre>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
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
