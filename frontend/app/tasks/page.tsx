"use client";

import { Button, Card, SectionHeader, TaskCard } from "@/components/design-system";
import { taskRecommendations } from "@/lib/mock-data";
import { useProductEvent } from "@/hooks/use-product-event";

export default function TaskCenterPage() {
  const track = useProductEvent();

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">Task Center</h1>
        <p className="page-subtitle">Priority, reason, and next action are visible on one screen.</p>
      </header>

      <Card>
        <SectionHeader title="Task Recommendations" subtitle="Integrated from project status, requests, and operational risk signals." />
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {taskRecommendations.map((task) => (
            <TaskCard
              key={task.id}
              title={task.title}
              project={task.project}
              due={task.due}
              priority={task.priority}
              status={task.status}
              reason={task.reason}
              actions={
                <>
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
