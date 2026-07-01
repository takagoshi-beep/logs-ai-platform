import Link from "next/link";
import { Button, Card } from "@/components/design-system";
import { projects, pastProposals, pastConsultations } from "@/lib/mock-data";

export default function HomePage() {
  const recentProjects = projects.slice(0, 3);
  const recentProposals = pastProposals.slice(0, 3);
  const recentConsultations = pastConsultations.slice(0, 3);

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">今日は何をしますか？</h1>
        <p className="page-subtitle">今日の仕事をここから始められます。</p>
      </header>

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
