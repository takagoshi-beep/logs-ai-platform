"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button, Card } from "@/components/design-system";
import { projects, pastProposals, pastConsultations } from "@/lib/mock-data";
import { getHome } from "@/lib/api-client";

interface HomeKpi {
  title: string;
  value: string | number;
  change: string;
  status: string;
}

const STATUS_COLOR: Record<string, string> = {
  success: "text-emerald-600",
  info: "text-sky-600",
  warning: "text-amber-600",
  error: "text-rose-600",
};

export default function HomePage() {
  const recentProjects = projects.slice(0, 3);
  const recentProposals = pastProposals.slice(0, 3);
  const recentConsultations = pastConsultations.slice(0, 3);

  const [kpis, setKpis] = useState<HomeKpi[]>([]);
  const [kpiError, setKpiError] = useState<string | null>(null);

  useEffect(() => {
    getHome().then((data: any) => {
      if (data?.success === false) {
        setKpiError(data.error ?? "データの取得に失敗しました");
        return;
      }
      setKpis(data?.kpis ?? []);
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
          <p className="text-sm font-semibold text-ink">最近開いた案件</p>
          <ul className="mt-3 space-y-2">
            {recentProjects.map((project) => (
              <li key={project.id}>
                <Link href={`/workspace/${project.id}`} className="text-sm text-accent hover:underline">
                  {project.name}
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <p className="text-sm font-semibold text-ink">最近作成した資料</p>
          <ul className="mt-3 space-y-2">
            {recentProposals.map((doc) => (
              <li key={doc.id} className="text-sm text-sub">
                {doc.title}
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <p className="text-sm font-semibold text-ink">最近相談した内容</p>
          <ul className="mt-3 space-y-2">
            {recentConsultations.map((chat) => (
              <li key={chat.id} className="text-sm text-sub">
                {chat.title}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}