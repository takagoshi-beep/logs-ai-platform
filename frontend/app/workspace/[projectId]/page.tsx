import { ActionPanel, Badge, Button, Card, ProjectCard, SectionHeader, StatusBadge, TaskCard, Timeline } from "@/components/design-system";
import { projects, taskRecommendations, workspaceHistory } from "@/lib/mock-data";

type Params = { params: { projectId: string } };

export default function WorkspacePage({ params }: Params) {
  const project = projects.find((item) => item.id === params.projectId) ?? projects[0];
  const projectTasks = taskRecommendations.filter((item) => item.project.toLowerCase().includes(project.name.split(" ")[0].toLowerCase()));

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">案件: {project.name}</h1>
        <p className="page-subtitle">案件の概要、タスク、資料、次の対応をまとめて確認します。</p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <ProjectCard name={project.name} summary={project.summary} owner={project.owner} status={project.status} />
        <ActionPanel
          title="次にやること"
          items={[
            { label: "最優先", value: "リスクアラートを確認し担当者を割り当てる" },
            { label: "次に対応", value: "提案資料のセクションを更新する" },
            { label: "その後", value: "関係者にフォローアップを送る" },
          ]}
          action={
            <Button href="/tasks" size="sm">
              関連タスクを見る
            </Button>
          }
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionHeader title="関連タスク" subtitle="この案件に紐づく対応です。" />
          <div className="mt-3 space-y-3">
            {(projectTasks.length ? projectTasks : taskRecommendations).map((task) => (
              <TaskCard
                key={task.id}
                title={task.title}
                project={task.project}
                due={task.due}
                priority={task.priority}
                status={task.status}
                reason={task.reason}
                actions={<Button tone="ghost" size="sm">タスクを開く</Button>}
              />
            ))}
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <SectionHeader title="AI相談" subtitle="この案件に関する最新の提案です。" />
            <p className="mt-3 text-sm text-sub">最新の提案</p>
            <p className="mt-1 text-sm">「納期までに仕入先確認と出荷枠の確保を最優先にしてください」</p>
            <div className="mt-3 flex items-center gap-2">
              <Badge label="判断に使った情報" />
              <Badge label="タスク履歴" />
              <Badge label="遅延傾向" />
            </div>
          </Card>

          <Card>
            <SectionHeader title="作成した資料" subtitle="作成済み・作成中の資料です。" />
            <ul className="mt-3 space-y-2 text-sm">
              <li className="surface-soft flex items-center justify-between p-3">
                <span>提案資料ドラフト v2 (pptx)</span>
                <StatusBadge status="準備完了" />
              </li>
              <li className="surface-soft flex items-center justify-between p-3">
                <span>フォローアップメール下書き</span>
                <StatusBadge status="保留" />
              </li>
              <li className="surface-soft flex items-center justify-between p-3">
                <span>実行ログ ex-1002</span>
                <StatusBadge status="承認済み" />
              </li>
            </ul>
          </Card>

          <Card>
            <SectionHeader title="活動履歴" subtitle="この案件で行われた対応の履歴です。" />
            <div className="mt-3">
              <Timeline items={workspaceHistory} />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
