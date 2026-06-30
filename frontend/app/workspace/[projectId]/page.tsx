import { ActionPanel, Badge, Button, Card, ProjectCard, SectionHeader, StatusBadge, TaskCard, Timeline } from "@/components/design-system";
import { projects, taskRecommendations, workspaceHistory } from "@/lib/mock-data";

type Params = { params: { projectId: string } };

export default function WorkspacePage({ params }: Params) {
  const project = projects.find((item) => item.id === params.projectId) ?? projects[0];
  const projectTasks = taskRecommendations.filter((item) => item.project.toLowerCase().includes(project.name.split(" ")[0].toLowerCase()));

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">Workspace: {project.name}</h1>
        <p className="page-subtitle">Project overview, tasks, artifacts, and next actions in one operating view.</p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <ProjectCard name={project.name} summary={project.summary} owner={project.owner} status={project.status} />
        <ActionPanel
          title="Next Action"
          items={[
            { label: "Primary", value: "Review risk alerts and assign owner" },
            { label: "Secondary", value: "Generate updated proposal section" },
            { label: "After", value: "Send follow-up to stakeholders" },
          ]}
          action={
            <Button href="/tasks" size="sm">
              Open Related Tasks
            </Button>
          }
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionHeader title="Related Tasks" subtitle="Action units linked to this project." />
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
                actions={<Button tone="ghost" size="sm">Open Task</Button>}
              />
            ))}
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <SectionHeader title="AI Conversation" subtitle="Recent project-specific recommendation." />
            <p className="mt-3 text-sm text-sub">Latest recommendation</p>
            <p className="mt-1 text-sm">"Prioritize supplier confirmation and shipment slot lock by EOD."</p>
            <div className="mt-3 flex items-center gap-2">
              <Badge label="Used Data" />
              <Badge label="Task History" />
              <Badge label="Delay Trend" />
            </div>
          </Card>

          <Card>
            <SectionHeader title="Artifacts" subtitle="Generated output grouped by execution stage." />
            <ul className="mt-3 space-y-2 text-sm">
              <li className="surface-soft flex items-center justify-between p-3">
                <span>Proposal draft v2 (pptx)</span>
                <StatusBadge status="Ready" />
              </li>
              <li className="surface-soft flex items-center justify-between p-3">
                <span>Follow-up mail draft</span>
                <StatusBadge status="Pending" />
              </li>
              <li className="surface-soft flex items-center justify-between p-3">
                <span>Execution log ex-1002</span>
                <StatusBadge status="Accepted" />
              </li>
            </ul>
          </Card>

          <Card>
            <SectionHeader title="History" subtitle="Workspace change timeline." />
            <div className="mt-3">
              <Timeline items={workspaceHistory} />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
