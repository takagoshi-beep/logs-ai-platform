import Link from "next/link";
import {
  ActionPanel,
  Alert,
  Badge,
  Button,
  Card,
  KpiCard,
  Progress,
  SectionHeader,
  StatusBadge,
} from "@/components/design-system";
import { aiSuggestions, alerts, inProgressWork, kpis, recommendedActions, todayUrgentCases } from "@/lib/mock-data";

export default function HomePage() {
  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">Home</h1>
        <p className="page-subtitle">Today first. Decide next action in under 30 seconds.</p>
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <KpiCard key={kpi.id} label={kpi.label} value={kpi.value} trend={kpi.trend} />
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <Card>
          <SectionHeader
            title="Cases Requiring Action Today"
            subtitle="Priority order is based on deadline and business impact."
            action={
              <Button href="/tasks" size="sm">
                Open Task Center
              </Button>
            }
          />
          <ul className="mt-4 space-y-3">
            {todayUrgentCases.map((item) => (
              <li key={item.id} className="surface-soft p-3">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <Badge label={item.project} />
                  <StatusBadge status={item.status} />
                </div>
                <p className="text-sm font-semibold text-ink">{item.title}</p>
                <p className="text-xs text-sub">Due: {item.due} | Owner: {item.owner}</p>
              </li>
            ))}
          </ul>
        </Card>

        <div className="space-y-4">
          {alerts.map((item) => (
            <Alert key={item.id} title={item.title} message={item.message} level={item.level as "high" | "medium"} />
          ))}
          <ActionPanel
            title="AI Summary"
            items={[
              { label: "Used Data", value: "Sales trend, task logs, project timeline" },
              { label: "Confirmation", value: "Manager approval still required" },
              { label: "Next Action", value: "Finalize owner assignment and send update" },
            ]}
            action={
              <Button href="/chat" tone="ghost" size="sm">
                Consult AI
              </Button>
            }
          />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionHeader title="Recommended Actions" subtitle="Clear next clicks to keep work moving." />
          <ul className="mt-3 space-y-2">
            {recommendedActions.map((item) => (
              <li key={item.id} className="surface-soft p-3">
                <p className="text-sm font-medium text-ink">{item.title}</p>
                <p className="mt-1 text-xs text-sub">{item.reason}</p>
                <Link className="mt-2 inline-block text-xs font-semibold text-accent" href={item.href}>
                  Open
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <SectionHeader title="In Progress Work" subtitle="Current execution status by project." />
          <ul className="mt-3 space-y-3">
            {inProgressWork.map((item) => (
              <li key={item.id}>
                <p className="text-sm font-medium text-ink">
                  {item.project} <span className="text-xs text-sub">| {item.stage}</span>
                </p>
                <p className="text-xs text-sub">Owner: {item.owner}</p>
                <div className="mt-2">
                  <Progress value={item.progress} label="Progress" />
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card>
        <SectionHeader title="AI Proposals" subtitle="Suggestions are shown as practical next actions, not abstract advice." />
        <ul className="mt-3 grid gap-3 md:grid-cols-2">
          {aiSuggestions.map((item) => (
            <li key={item.id} className="surface-soft p-3">
              <p className="text-sm font-medium text-ink">{item.title}</p>
              <p className="mt-1 text-xs text-sub">{item.confidence}</p>
              <p className="mt-1 text-xs text-sub">Next: {item.next}</p>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
