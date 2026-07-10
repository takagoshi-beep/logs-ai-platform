"use client";

import { useEffect, useState } from "react";
import { Badge, Button, Card, SectionHeader, StatusBadge, TaskCard, Timeline } from "@/components/design-system";
import { getProject } from "@/lib/api-client";

type Params = { params: { projectId: string } };

interface ProjectAction {
  action_id: string;
  title: string;
  description: string;
  condition: string;
  priority: string;
  confidence: number;
  due_date: string | null;
}

interface ProjectEvent {
  event_id: string;
  business_meaning: string;
  impact_summary: string;
  event_time: string;
}

interface ProductionStatus {
  po_number: string;
  status: string | null;
  factory: string | null;
  production_staff: string | null;
  pp: string | null;
  pp_expected_date: string | null;
  pp_approved_date: string | null;
  top: string | null;
  top_expected_date: string | null;
  top_approved_date: string | null;
  ex_factory: string | null;
  etd: string | null;
  eta: string | null;
  customs_clearance: string | null;
  delivery_date: string | null;
  project_name: string | null;
}

interface RelatedMessage {
  status: string;
  summary: string;
  records: Array<Record<string, any>>;
  match_type?: string;
}

interface RelatedCommunications {
  gmail: RelatedMessage;
  slack: RelatedMessage;
}

interface ProjectDetail {
  project_id: string;
  po_number: string;
  state: string;
  status_badges: string[];
  priority: string;
  delivery_month_bucket: string | null;
  data: {
    customer_name: string;
    supplier_name: string;
    days_until_delivery: number;
    po_amount: number | null;
    cost_amount: number | null;
    sale_amount: number | null;
    gross_profit: number | null;
    gross_profit_margin: number | null;
    actual_cost_total: number | null;
    actual_gross_profit: number | null;
    actual_gross_profit_margin: number | null;
    project_name: string | null;
    planned_import_cost_ratio: number | null;
    actual_import_cost_ratio: number | null;
  };
  actions: ProjectAction[];
  events: { count: number; items: ProjectEvent[] };
}

// 2026-07-09（14.39、Noritsuguの指定）: 状態は「完了」（売上・仕入とも
// 入力済み）以外は「売上未確定」「原価未確定」が同時に表示されうる。
// 納期超過は廃止した。
const STATE_LABEL: Record<string, string> = {
  completed: "売上・仕入計上済",
  sales_unconfirmed: "売上未確定",
  cost_unconfirmed: "原価未確定",
  po_issued: "PO発行済み",
  po_not_issued: "PO未発行",
  delivery_completed_by_production: "納品完了（生産管理）",
};

// 2026-07-09（14.35）: 健全性・リスク・推奨対応を廃止し、現在から納品日
// までの月数だけで判定する単純なバッジに置き換えた（Noritsuguの指定）。
// 14.38: a/b/cは指示を分かりやすくするための記号だったため表示からは
// 削除。既に納期を過ぎている場合はバッジ自体を表示しない
// （delivery_month_bucketがnullになる）。
const DELIVERY_BUCKET_LABEL: Record<string, string> = {
  this_month: "今月納品予定",
  next_month: "来月納品予定",
  month_after_next_or_later: "再来月以降納品予定",
};

function fmtYen(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${Math.round(v).toLocaleString()}円`;
}

export default function WorkspacePage({ params }: Params) {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [production, setProduction] = useState<ProductionStatus[]>([]);
  const [related, setRelated] = useState<RelatedCommunications | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProject(params.projectId).then((data: any) => {
      setLoading(false);
      if (data?.success === false) {
        setError(data.error ?? "案件データの取得に失敗しました");
        return;
      }
      setProject(data?.project ?? null);
      setProduction(data?.production ?? []);
      setRelated(data?.related_communications ?? null);
    });
  }, [params.projectId]);

  if (loading) {
    return <p className="px-4 py-8 text-center text-sm text-sub">読み込み中...</p>;
  }

  if (error || !project) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        {error ?? "案件が見つかりませんでした"}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">
          案件: {project.po_number}
          {project.data.project_name && `（${project.data.project_name}）`}
        </h1>
        <p className="page-subtitle">Supabase（purchase_orders）の実データに基づく分析です。</p>
      </header>

      <div className="grid gap-4">
        <Card>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-ink">{project.data.customer_name}</h3>
            <div className="flex flex-wrap gap-1">
              {(project.status_badges ?? []).map((badge) => (
                <StatusBadge key={badge} status={STATE_LABEL[badge] ?? badge} />
              ))}
            </div>
          </div>
          <p className="text-sm text-sub">仕入先: {project.data.supplier_name}</p>
          <p className="mt-2 text-xs text-sub">
            {project.data.days_until_delivery < 0 ? "納期経過" : `納期まで: ${project.data.days_until_delivery}日`}
          </p>
          <div className="mt-3 text-xs">売上金額: {fmtYen(project.data.sale_amount)}</div>
          <table className="mt-2 w-full text-xs">
            <thead>
              <tr className="text-sub">
                <th className="text-left font-normal"></th>
                <th className="text-right font-normal">予定（PO）</th>
                <th className="text-right font-normal">実績（仕入確定）</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="py-0.5">原価</td>
                <td className="py-0.5 text-right">{fmtYen(project.data.cost_amount)}</td>
                <td className="py-0.5 text-right">{fmtYen(project.data.actual_cost_total)}</td>
              </tr>
              <tr>
                <td className="py-0.5">粗利</td>
                <td className="py-0.5 text-right">{fmtYen(project.data.gross_profit)}</td>
                <td className="py-0.5 text-right">{fmtYen(project.data.actual_gross_profit)}</td>
              </tr>
              <tr>
                <td className="py-0.5">粗利率</td>
                <td className="py-0.5 text-right">{project.data.gross_profit_margin != null ? `${project.data.gross_profit_margin.toFixed(1)}%` : "—"}</td>
                <td className="py-0.5 text-right">{project.data.actual_gross_profit_margin != null ? `${project.data.actual_gross_profit_margin.toFixed(1)}%` : "—"}</td>
              </tr>
            </tbody>
          </table>
          <p className="mt-1 text-xs text-sub">
            予定はPOの見積もり（合計売上原価）、実績は仕入確定後の諸掛込原価（PO単位の合計）を使用。売上金額はPOの値のまま比較しています。
          </p>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs border-t border-slate-100 pt-3">
            <div>
              予定輸入経費率: {project.data.planned_import_cost_ratio != null ? project.data.planned_import_cost_ratio.toFixed(2) : "—"}
              <span className="ml-1 text-sub">（PO入力時点）</span>
            </div>
            <div>
              実績輸入経費率: {project.data.actual_import_cost_ratio != null ? project.data.actual_import_cost_ratio.toFixed(2) : "—"}
              <span className="ml-1 text-sub">（仕入確定後）</span>
            </div>
          </div>
          <p className="mt-1 text-xs text-sub">
            輸入経費率＝諸掛込原価÷商品原価（商品単価×数量×為替）。1.xxの値で、予定と実績を比較して予実管理に使います。
          </p>
          {project.delivery_month_bucket && (
            <div className="mt-3">
              <Badge label={DELIVERY_BUCKET_LABEL[project.delivery_month_bucket] ?? project.delivery_month_bucket} />
            </div>
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionHeader title="関連タスク" subtitle="この案件から実データに基づいて生成されたAIの推奨対応です。" />
          <div className="mt-3 space-y-3">
            {project.actions.length > 0 ? (
              project.actions.map((action) => (
                <TaskCard
                  key={action.action_id}
                  title={action.title}
                  project={project.po_number}
                  due={action.due_date ? new Date(action.due_date).toLocaleDateString("ja-JP") : "—"}
                  priority={action.priority}
                  status="未着手"
                  reason={action.condition || action.description}
                  actions={<Button tone="ghost" size="sm">タスクを開く</Button>}
                />
              ))
            ) : (
              <p className="text-sm text-sub">現時点で推奨タスクはありません</p>
            )}
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <SectionHeader title="活動履歴" subtitle="この案件で検知された実際のイベントです。" />
            <div className="mt-3">
              {project.events.items.length > 0 ? (
                <Timeline
                  items={project.events.items.map((e) => ({
                    id: e.event_id,
                    title: e.business_meaning,
                    time: new Date(e.event_time).toLocaleString("ja-JP"),
                    detail: e.impact_summary,
                  }))}
                />
              ) : (
                <p className="text-sm text-sub">イベントはまだ記録されていません</p>
              )}
            </div>
          </Card>
        </div>
      </div>

      {production.length > 0 && (
        <Card>
          <SectionHeader
            title="生産進捗"
            subtitle="生産管理チームのスプレッドシートから同期された、量産の工程状況です（PO番号で突合）。表示項目は全て量産シート自体の列で、PO側の情報で補ってはいません。"
          />
          <div className="mt-3 space-y-3">
            {production.map((p, idx) => (
              <div key={idx} className="rounded-lg border border-slate-200 p-4">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-ink">{p.project_name || "案件名: データなし"}</p>
                  <Badge label={p.status || "ステータス: データなし"} />
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-sub sm:grid-cols-3">
                  <div>工場: {p.factory || "データなし"}</div>
                  <div>生産担当: {p.production_staff || "データなし"}</div>
                  <div>PP予定: {p.pp_expected_date || "データなし"}</div>
                  <div>TOP予定: {p.top_expected_date || "データなし"}</div>
                  <div>ETD: {p.etd || "データなし"}</div>
                  <div>ETA: {p.eta || "データなし"}</div>
                  <div>納品日: {p.delivery_date || "データなし"}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
      {related && (
        <Card>
          <SectionHeader
            title="関連するメール・Slack"
            subtitle="PO番号・顧客担当者のメールアドレスで、あなた自身のGmail/Slackから検索した結果です。"
          />
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <div>
              <h4 className="mb-2 text-xs font-semibold text-ink">Gmail</h4>
              {related.gmail.status === "ok" && related.gmail.records.length > 0 ? (
                <div className="space-y-2">
                  {related.gmail.match_type === "customer_contact" && (
                    <p className="text-xs text-amber-700">※PO番号の一致ではなく、この顧客の担当者とのメールです（同じ案件とは限りません）。</p>
                  )}
                  {related.gmail.records.map((r, idx) => (
                    <div key={idx} className="rounded-lg border border-slate-200 p-3 text-xs">
                      <p className="font-medium text-ink">{r.subject}</p>
                      <p className="text-sub">{r.from} ・ {r.date}</p>
                      {r.snippet && <p className="mt-1 text-sub">{r.snippet}</p>}
                    </div>
                  ))}
                </div>
              ) : related.gmail.status === "unavailable" ? (
                <p className="text-xs text-sub">
                  {related.gmail.summary}{" "}
                  <a href="/settings" className="text-accent hover:underline">設定画面へ</a>
                </p>
              ) : (
                <p className="text-xs text-sub">{related.gmail.summary || "関連するメールは見つかりませんでした。"}</p>
              )}
            </div>
            <div>
              <h4 className="mb-2 text-xs font-semibold text-ink">Slack</h4>
              {related.slack.status === "ok" && related.slack.records.length > 0 ? (
                <div className="space-y-2">
                  {related.slack.records.map((r, idx) => (
                    <div key={idx} className="rounded-lg border border-slate-200 p-3 text-xs">
                      <p className="font-medium text-ink">#{r.channel} ・ {r.username}</p>
                      <p className="mt-1 text-sub">{r.text}</p>
                    </div>
                  ))}
                </div>
              ) : related.slack.status === "unavailable" ? (
                <p className="text-xs text-sub">
                  {related.slack.summary}{" "}
                  <a href="/settings" className="text-accent hover:underline">設定画面へ</a>
                </p>
              ) : (
                <p className="text-xs text-sub">{related.slack.summary || "関連するメッセージは見つかりませんでした。"}</p>
              )}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}