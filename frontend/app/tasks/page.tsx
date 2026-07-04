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

  useEffect(() => {
    async function loadTasks() {
      try {
        const response = await getTodayActions(50);
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
      } finally {
        setIsLoading(false);
      }
    }

    loadTasks();
  }, []);

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="page-title">今日のタスク</h1>
            <p className="page-subtitle">優先度・理由・次の対応を1画面で確認できます。</p>
            {usedRealData && <p className="text-xs text-green-600 mt-2">最新データを表示中</p>}
            {!usedRealData && !isLoading && <p className="text-xs text-orange-600 mt-2">サンプルデータを表示中</p>}
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
                <div key={task.id} className="surface-soft p-4 rounded-lg border border-slate-200">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-base font-semibold text-ink">{task.title}</p>
                    <span className="text-xs font-semibold text-accent whitespace-nowrap">{priorityLabel(task.priority)}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-sub">
                    <span>{task.project}</span>
                    <span>期限: {task.due}</span>
                    <span>担当: {task.owner || "-"}</span>
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