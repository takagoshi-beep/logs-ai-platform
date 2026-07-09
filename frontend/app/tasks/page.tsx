"use client";

import { Button, Card, SectionHeader } from "@/components/design-system";
import { taskRecommendations } from "@/lib/mock-data";
import { getTodayActions } from "@/lib/api-client";
import { useProductEvent } from "@/hooks/use-product-event";
import { useEffect, useState } from "react";

interface Task {
  id: string;
  title: string;
  project: string;
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
  gmail_unread?: number;
  slack_recent?: number;
}

interface Signals {
  gmail_unread_total: number;
  slack_recent_total: number;
  gmail_status: string;
  slack_status: string;
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
  const track = useProductEvent();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [usedRealData, setUsedRealData] = useState(false);
  const [scopeChoice, setScopeChoice] = useState<"mine" | "all">("mine");
  const [signals, setSignals] = useState<Signals | null>(null);

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
            gmail_unread: action.gmail_unread || 0,
            slack_recent: action.slack_recent || 0,
          }));
          setTasks(mappedTasks);
          setSignals(response.signals ?? null);
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

      {!isLoading && signals && (
        <div className="flex flex-wrap gap-4 rounded-lg border border-slate-200 bg-white p-3 text-sm text-sub">
          <span>
            📧 関連する未読メール:{" "}
            {signals.gmail_status === "ok" ? (
              <strong className="text-ink">{signals.gmail_unread_total}件</strong>
            ) : signals.gmail_status === "unavailable" ? (
              <span className="text-amber-700">Gmail未連携 (<a href="/settings" className="underline">設定画面へ</a>)</span>
            ) : (
              <span className="text-amber-700">取得エラー</span>
            )}
          </span>
          <span>
            💬 関連する直近のSlackメッセージ:{" "}
            {signals.slack_status === "ok" ? (
              <strong className="text-ink">{signals.slack_recent_total}件</strong>
            ) : signals.slack_status === "unavailable" ? (
              <span className="text-amber-700">Slack未連携 (<a href="/settings" className="underline">設定画面へ</a>)</span>
            ) : (
              <span className="text-amber-700">取得エラー</span>
            )}
          </span>
        </div>
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
                <div key={task.id} className="surface-soft p-4 rounded-lg border border-slate-200">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-base font-semibold text-ink">{task.title}</p>
                    <span className="text-xs font-semibold text-accent whitespace-nowrap">{priorityLabel(task.priority)}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-sub">
                    <span>{task.project}</span>
                    <span>期限: {task.due}</span>
                    <span>担当: {task.owner || "-"}</span>
                    {!!task.gmail_unread && (
                      <span className="text-amber-700">📧未読{task.gmail_unread}件</span>
                    )}
                    {!!task.slack_recent && (
                      <span className="text-amber-700">💬関連{task.slack_recent}件</span>
                    )}
                  </div>
                  {task.reason && (
                    <p className="mt-2 text-xs text-sub">理由: {task.reason}</p>
                  )}
                  <div className="flex gap-2 mt-3">
                    <Button
                      size="sm"
                      onClick={() =>
                        track({
                          event_id: crypto.randomUUID(),
                          user_id: "u-demo",
                          role: "sales",
                          screen: "task_center",
                          action: "click",
                          target_type: "task_ai_consult",
                          target_id: task.id,
                          timestamp: new Date().toISOString(),
                          metadata: { task_title: task.title },
                        })
                      }
                    >
                      AIに相談
                    </Button>
                    <Button tone="ghost" size="sm">
                      タスクを開く
                    </Button>
                  </div>
                </div>
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