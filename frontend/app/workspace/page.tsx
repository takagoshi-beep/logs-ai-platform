"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/design-system";
import { getProjects } from "@/lib/api-client";

interface ApiProject {
  project_id: string;
  project_name: string;
  project_title: string | null;
  customer: string;
  state: string;
  status_badges: string[];
  priority: string;
  actions_count: number;
  events_count: number;
  trace_id: string;
}

// 2026-07-09（14.39、Noritsuguの指定）: 状態は「完了」（売上・仕入とも
// 入力済み）以外は「売上未確定」「原価未確定」が同時に表示されうる。
// 納期超過は廃止した。
const STATE_LABEL: Record<string, string> = {
  completed: "完了",
  sales_unconfirmed: "売上未確定",
  cost_unconfirmed: "原価未確定",
  po_issued: "PO発行済み",
  po_not_issued: "PO未発行",
};

export default function WorkspaceListPage() {
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [scopeChoice, setScopeChoice] = useState<"mine" | "all">("mine");
  const [projects, setProjects] = useState<ApiProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getProjects(50, scopeChoice).then((data: any) => {
      setLoading(false);
      if (data?.success === false) {
        setError(data.error ?? "データの取得に失敗しました");
        return;
      }
      setError(null);
      setProjects(data?.projects ?? []);
    });
  }, [scopeChoice]);

  const states = Array.from(new Set(projects.flatMap((p) => p.status_badges ?? [])));

  const filtered = projects.filter((p) => {
    if (search && !p.project_name.toLowerCase().includes(search.toLowerCase()) &&
        !(p.project_title ?? "").toLowerCase().includes(search.toLowerCase()) &&
        !p.customer.toLowerCase().includes(search.toLowerCase())) return false;
    if (stateFilter !== "all" && !(p.status_badges ?? []).includes(stateFilter)) return false;
    return true;
  });

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">案件</h1>
        <p className="page-subtitle">Supabase（発注依頼・purchase_orders）の実データを表示しています</p>
      </header>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          {error}
        </div>
      )}

      {!loading && !error && scopeChoice === "mine" && projects.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-sub">
          関連する案件が見つかりませんでした（社員マスタの氏名と、PO上の担当者名が一致しない可能性があります）。「すべての案件」に切り替えてご覧いただけます。
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5 text-sm">
          <button
            onClick={() => setScopeChoice("mine")}
            className={`rounded-md px-3 py-1.5 font-medium transition ${
              scopeChoice === "mine" ? "bg-accent text-white" : "text-ink hover:bg-slate-100"
            }`}
          >
            自分の案件
          </button>
          <button
            onClick={() => setScopeChoice("all")}
            className={`rounded-md px-3 py-1.5 font-medium transition ${
              scopeChoice === "all" ? "bg-accent text-white" : "text-ink hover:bg-slate-100"
            }`}
          >
            すべての案件
          </button>
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="案件名・顧客名で検索"
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <select
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value)}
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="all">状態: すべて</option>
          {states.map((s) => (
            <option key={s} value={s}>
              {STATE_LABEL[s] ?? s}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="grid grid-cols-3 gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-medium text-sub">
          <span>案件名</span>
          <span>顧客</span>
          <span>状態</span>
        </div>
        {loading && (
          <p className="px-4 py-8 text-center text-sm text-sub">読み込み中...</p>
        )}
        {!loading && filtered.map((project) => (
          <Link
            key={project.project_id}
            href={`/workspace/${project.project_id}`}
            className="grid grid-cols-3 items-center gap-2 border-b border-slate-100 px-4 py-3 text-sm text-ink last:border-b-0 hover:bg-slate-50"
          >
            <span className="font-medium">
              {project.project_title || project.project_name}
              {project.project_title && <span className="ml-2 text-xs text-sub">{project.project_name}</span>}
            </span>
            <span className="text-sub">{project.customer}</span>
            <span className="flex flex-wrap gap-1">
              {(project.status_badges ?? []).map((badge) => (
                <StatusBadge key={badge} status={STATE_LABEL[badge] ?? badge} />
              ))}
            </span>
          </Link>
        ))}
        {!loading && filtered.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-sub">該当する案件がありません</p>
        )}
      </div>
    </div>
  );
}