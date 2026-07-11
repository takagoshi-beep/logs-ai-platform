"use client";

import { Card, SectionHeader } from "@/components/design-system";
import { taskRecommendations } from "@/lib/mock-data";
import { getTodayActions } from "@/lib/api-client";
import Link from "next/link";
import { useEffect, useState } from "react";

interface Task {
  id: string;
  title: string;
  project: string;
  project_id?: string;
  project_title?: string;
  customer?: string;
  owner?: string;
  due: string;
  priority: string;
  status: string;
  reason: string;
  action_id?: string;
  trace_id?: string;
  related_state?: string;
  related_goal?: string;
}

function priorityLabel(p: string) {
  switch (p?.toLowerCase()) {
    case "high":
      return "高";
    case "medium":
      return "中";
    case "low":
      return "低";
    default:
      return p;
  }
}

function priorityRank(p: string) {
  switch (p?.toLowerCase()) {
    case "high":
      return 0;
    case "medium":
      return 1;
    case "low":
      return 2;
    default:
      return 3;
  }
}

export default function TaskCenterPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [usedRealData, setUsedRealData] = useState(false);
  const [scopeChoice, setScopeChoice] = useState<"mine" | "all">("mine");

  useEffect(() => {
    async function loadTasks() {
      setIsLoading(true);
      try {
        const response = await getTodayActions(50, scopeChoice);
        if (response.success && response.actions) {
          const mappedTasks: Task[] = response.actions.map((action: any, idx: number) => ({
            id: action.action_id || `task-${idx}`,
            title: action.title,
            project: action.project_name || "System",
            project_id: action.project_id,
            project_title: action.project_title,
            customer: action.customer,
            owner: action.customer || "-",
            due: "本日",
            priority: action.priority || "medium",
            status: action.related_state || "pending",
            reason: action.reason || "",
            action_id: action.action_id,
            trace_id: action.trace_id,
            related_state: action.related_state,
            related_goal: action.related_goal,
          }));
          setTasks(mappedTasks);
          setUsedRealData(true);
        } else {
          throw new Error("No actions returned");
        }
      } catch (error) {
        console.error("Failed to load tasks from API, using mock data:", error);
        const mockTasks: Task[] = taskRecommendations.map((task: any) => ({
          id: task.id,
          title: task.title,
          project: task.project,
          owner: task.owner,
          due: task.due,
          priority: task.priority,
          status: task.status,
          reason: task.reason,
        }));
        setTasks(mockTasks);
        setSignals(null);
      } finally {
        setIsLoading(false);
      }
    }

    loadTasks();
  }, [scopeChoice]);

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="page-title">今日のタスク</h1>
            <p className="page-subtitle">優先度・理由・次の対応を1画面で確認できます。</p>
            {usedRealData && <p className="text-xs text-green-600 mt-2">最新データを表示中</p>}
            {!usedRealData && !isLoading && <p className="text-xs text-orange-600 mt-2">サンプルデータを表示中</p>}
          </div>
          <div className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5 text-sm">
            <button
              onClick={() => setScopeChoice("mine")}
              className={`rounded-md px-3 py-1.5 font-medium transition ${
                scopeChoice === "mine" ? "bg-accent text-white" : "text-ink hover:bg-slate-100"
              }`}
            >
              自分のタスク
            </button>
            <button
              onClick={() => setScopeChoice("all")}
              className={`rounded-md px-3 py-1.5 font-medium transition ${
                scopeChoice === "all" ? "bg-accent text-white" : "text-ink hover:bg-slate-100"
              }`}
            >
              すべてのタスク
            </button>
          </div>
        </div>
      </header>

      {isLoading && (
        <Card>
          <p className="text-center py-8 text-gray-500">タスクを読み込み中です...</p>
        </Card>
      )}

      {!isLoading && (
        <Card>
          <SectionHeader
            title="今日のおすすめタスク"
            subtitle="案件状況、依頼内容、リスクをもとに表示しています。"
          />
          <div className="mt-4 space-y-3">
            {[...tasks]
              .sort((a, b) => priorityRank(a.priority) - priorityRank(b.priority))
              .map((task) => (
                <Link
                  key={task.id}
                  href={task.project_id ? `/workspace/${task.project_id}` : "#"}
                  className="surface-soft block p-4 rounded-lg border border-slate-200 hover:bg-slate-50"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-base font-semibold text-ink">{task.title}</p>
                    <span className="text-xs font-semibold text-accent whitespace-nowrap">{priorityLabel(task.priority)}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-sub">
                    <span>
                      {task.project}
                      {task.project_title && `（${task.project_title}）`}
                    </span>
                    <span>担当: {task.owner || "-"}</span>
                  </div>
                  {task.reason && (
                    <p className="mt-2 text-xs text-sub">理由: {task.reason}</p>
                  )}
                </Link>
              ))}
          </div>
          {tasks.length === 0 && (
            <p className="text-center py-8 text-gray-500">表示できるタスクがありません</p>
          )}
        </Card>
      )}
    </div>
  );
}