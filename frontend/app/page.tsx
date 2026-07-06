"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button, Card } from "@/components/design-system";
import { getHome } from "@/lib/api-client";

interface HomeKpi {
  title: string;
  value: string | number;
  change: string;
  status: string;
}

interface RecentProject {
  project_id: string;
  name: string;
}

interface RecentActivity {
  recent_questions: string[];
  recent_documents: string[];
  recent_projects: RecentProject[];
}

const STATUS_COLOR: Record<string, string> = {
  success: "text-emerald-600",
  info: "text-sky-600",
  warning: "text-amber-600",
  error: "text-rose-600",
};

export default function HomePage() {
  const [kpis, setKpis] = useState<HomeKpi[]>([]);
  const [kpiError, setKpiError] = useState<string | null>(null);
  const [activity, setActivity] = useState<RecentActivity | null>(null);

  useEffect(() => {
    getHome().then((data: any) => {
      if (data?.success === false) {
        setKpiError(data.error ?? "データの取得に失敗しました");
        return;
      }
      setKpis(data?.kpis ?? []);
      setActivity(data?.recent_activity ?? null);
      if (data?.alerts?.length) {
        setKpiError(data.alerts[0]?.message ?? null);
      }
    });
  }, []);

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">今日は何をしますか？</h1>
        <p className="page-subtitle">今日の仕事をここから始められます。</p>
      </header>

      {kpiError && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          {kpiError}
        </div>
      )}

      {kpis.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {kpis.map((kpi) => (
            <Card key={kpi.title}>
              <p className="text-xs font-medium text-sub">{kpi.title}</p>
              <p className={`mt-1 text-2xl font-semibold ${STATUS_COLOR[kpi.status] ?? "text-ink"}`}>
                {kpi.value}
              </p>
              {kpi.change && <p className="mt-1 text-xs text-sub">{kpi.change}</p>}
            </Card>
          ))}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Button href="/workspace" size="md" className="h-20 w-full text-base">
          案件を見る
        </Button>
        <Button href="/tasks" size="md" className="h-20 w-full text-base">
          今日のタスクを見る
        </Button>
        <Button href="/proposals" size="md" className="h-20 w-full text-base">
          資料を作成する
        </Button>
        <Button href="/chat" size="md" className="h-20 w-full text-base">
          AIに相談する
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <p className="text-sm font-semibold text-ink">案件（実データ）</p>
          <ul className="mt-3 space-y-2">
            {activity?.recent_projects?.length ? (
              activity.recent_projects.map((project) => (
                <li key={project.project_id}>
                  <Link href={`/workspace/${project.project_id}`} className="text-sm text-accent hover:underline">
                    {project.name}
                  </Link>
                </li>
              ))
            ) : (
              <li className="text-sm text-sub">案件はありません</li>
            )}
          </ul>
        </Card>

        <Card>
          <p className="text-sm font-semibold text-ink">最近作成した提案書</p>
          <ul className="mt-3 space-y-2">
            {activity?.recent_documents?.length ? (
              activity.recent_documents.map((title, idx) => (
                <li key={idx} className="text-sm text-sub">
                  {title}
                </li>
              ))
            ) : (
              <li className="text-sm text-sub">まだ作成した提案書はありません</li>
            )}
          </ul>
        </Card>

        <Card>
          <p className="text-sm font-semibold text-ink">最近相談した内容</p>
          <ul className="mt-3 space-y-2">
            {activity?.recent_questions?.length ? (
              activity.recent_questions.map((question, idx) => (
                <li key={idx} className="text-sm text-sub">
                  {question}
                </li>
              ))
            ) : (
              <li className="text-sm text-sub">まだ相談した内容はありません</li>
            )}
          </ul>
        </Card>
      </div>
    </div>
  );
}