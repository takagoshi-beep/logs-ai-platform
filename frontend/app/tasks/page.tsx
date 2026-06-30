"use client";

import Link from "next/link";
import { Button, Card, SectionHeader, TaskCard, Badge } from "@/components/design-system";
import { taskRecommendations } from "@/lib/mock-data";
import { getTodayActions } from "@/lib/api-client";
import { useProductEvent } from "@/hooks/use-product-event";
import { useEffect, useState } from "react";

interface Task {
  id: string;
  title: string;
  project: string;
  customer?: string;
  due: string;
  priority: string;
  status: string;
  reason: string;
  action_id?: string;
  trace_id?: string;
  related_state?: string;
  related_goal?: string;
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
            due: "Today",
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
            <h1 className="page-title">Task Center</h1>
            <p className="page-subtitle">Priority, reason, and next action are visible on one screen.</p>
            {usedRealData && <p className="text-xs text-green-600 mt-2">Using real ProjectAggregate data</p>}
            {!usedRealData && !isLoading && <p className="text-xs text-orange-600 mt-2">Using fallback mock data</p>}
          </div>
        </div>
      </header>

      {isLoading && (
        <Card>
          <p className="text-center py-8 text-gray-500">Loading tasks...</p>
        </Card>
      )}

      {!isLoading && (
        <Card>
          <SectionHeader
            title="Task Recommendations"
            subtitle="Integrated from project status, requests, and operational risk signals."
          />
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {tasks.map((task) => (
              <div key={task.id} className="surface-soft p-4 rounded-lg border border-slate-200">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex gap-2 flex-wrap">
                    {task.project && <Badge label={task.project} />}
                    {task.customer && <Badge label={task.customer} />}
                  </div>
                  <span className="text-xs font-semibold text-accent">{task.priority}</span>
                </div>
                <p className="font-semibold text-sm">{task.title}</p>
                {task.reason && <p className="text-xs text-gray-600 mt-1">{task.reason}</p>}
                {task.related_state && <p className="text-xs text-gray-500 mt-1">State: {task.related_state}</p>}
                {task.related_goal && <p className="text-xs text-gray-500">Goal: {task.related_goal}</p>}
                <div className="flex gap-2 mt-3">
                  {task.trace_id && (
                    <Link href={`/debug?trace=${task.trace_id}`} className="text-xs text-blue-500 hover:underline">
                      View Trace
                    </Link>
                  )}
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
                    完了
                  </Button>
                </div>
              </div>
            ))}
          </div>
          {tasks.length === 0 && (
            <p className="text-center py-8 text-gray-500">No tasks available</p>
          )}
        </Card>
      )}
    </div>
  );
}

                  </Button>
                  <Button tone="ghost" size="sm">
                    保留
                  </Button>
                  <Button tone="neutral" size="sm">
                    詳細確認
                  </Button>
                </>
              }
            />
          ))}
        </div>
      </Card>
    </div>
  );
}
