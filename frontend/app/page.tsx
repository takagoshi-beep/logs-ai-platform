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
import { getTodayActions, getProjects, getHome } from "@/lib/api-client";

interface HomeData {
  trace_id?: string;
  kpis?: Array<{
    id?: string;
    title?: string;
    value?: string | number;
    change?: string;
    status?: string;
    label?: string;
    trend?: string;
  }>;
  today_actions?: Array<{
    title?: string;
    description?: string;
    priority?: string;
    reason?: string;
    source_table?: string;
    source_count?: number;
  }>;
  alerts?: Array<{
    id?: string;
    title?: string;
    message?: string;
    type?: string;
    details?: string;
    level?: string;
  }>;
  data_sources?: string[];
}

export default async function HomePage() {
  let homeData: HomeData = {};
  let hasError = false;
  let usedRealData = false;

  // Try to fetch real data from ProjectAggregate API
  try {
    const todayActionsResponse = await getTodayActions(10);
    if (todayActionsResponse.success && todayActionsResponse.actions) {
      usedRealData = true;
      homeData = {
        trace_id: todayActionsResponse.actions[0]?.trace_id,
        today_actions: todayActionsResponse.actions.map((action: any) => ({
          title: action.title,
          description: action.description,
          priority: action.priority,
          reason: action.reason,
          source_table: action.related_event || "Project",
          source_count: 1,
          project_id: action.project_id,
          project_name: action.project_name,
          customer: action.customer,
          action_id: action.action_id,
          related_state: action.related_state,
          related_goal: action.related_goal,
          trace_id: action.trace_id,
        })),
        alerts: [],
        kpis: [
          {
            id: "kpi-1",
            title: "Active Projects",
            value: todayActionsResponse.count || 0,
            change: "from API",
            status: "info",
          },
          {
            id: "kpi-2",
            title: "High Priority Actions",
            value: todayActionsResponse.actions?.filter((a: any) => a.priority === "high").length || 0,
            change: "urgent",
            status: "warning",
          },
          {
            id: "kpi-3",
            title: "Total Actions",
            value: todayActionsResponse.total || 0,
            change: "all projects",
            status: "success",
          },
          {
            id: "kpi-4",
            title: "Data Source",
            value: "Live",
            change: "real-time",
            status: "success",
          },
        ],
        data_sources: ["Projects API", "ProjectAggregate", "Events"],
      };
    } else {
      hasError = true;
      console.warn("Failed to fetch today actions:", todayActionsResponse.error);
    }
  } catch (error) {
    hasError = true;
    console.error("Error fetching today actions:", error);
  }

  // Fallback to old home data API if ProjectAggregate API fails
  if (hasError || !usedRealData) {
    try {
      const response = await getHome();
      if (response.success) {
        homeData = response as HomeData;
      }
    } catch (fallbackError) {
      console.error("Fallback home API also failed:", fallbackError);
    }
  }

  // Use real data if available, otherwise fall back to mock data
  const displayKpis = homeData.kpis && homeData.kpis.length > 0
    ? homeData.kpis.map((kpi, idx) => ({
        id: `kpi-${idx}`,
        label: kpi.title || kpi.label || "",
        value: kpi.value || "",
        trend: kpi.change || kpi.trend || "",
      }))
    : kpis;

  const displayAlerts = homeData.alerts && homeData.alerts.length > 0
    ? homeData.alerts.map((alert, idx) => ({
        id: `alert-${idx}`,
        title: alert.title || "Alert",
        message: alert.message || alert.details || "",
        level: alert.type === "warning" ? "high" : alert.type === "error" ? "high" : "medium",
      }))
    : alerts;

  const displayTodayActions = homeData.today_actions && homeData.today_actions.length > 0
    ? homeData.today_actions.map((action: any, idx) => ({
        id: `action-${idx}`,
        project: action.project_name || "System",
        customer: action.customer || "",
        status: action.priority || "info",
        title: action.title || "",
        due: action.due_date ? new Date(action.due_date).toLocaleDateString() : "Today",
        owner: action.customer || "AI",
        description: action.description || "",
        reason: action.reason || "",
        source_table: action.source_table || "",
        action_id: action.action_id,
        project_id: action.project_id,
        trace_id: action.trace_id,
        related_state: action.related_state,
      }))
    : todayUrgentCases;

  const traceId = homeData.trace_id || "trace-home-fallback";

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="page-title">Home</h1>
            <p className="page-subtitle">Today first. Decide next action in under 30 seconds.</p>
            {usedRealData && <p className="text-xs text-green-600 mt-2">Using real ProjectAggregate data</p>}
            {hasError && !usedRealData && <p className="text-xs text-orange-600 mt-2">Using fallback mock data</p>}
          </div>
          {traceId && !hasError && (
            <Link href={`/debug?trace=${traceId}`} className="text-xs text-blue-600 hover:underline">
              View Trace
            </Link>
          )}
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {displayKpis.map((kpi) => (
          <KpiCard key={kpi.id} label={kpi.label} value={String(kpi.value)} trend={kpi.trend} />
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
            {displayTodayActions.map((item: any) => (
              <li key={item.id} className="surface-soft p-3">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <Badge label={item.project} />
                  <StatusBadge status={item.status} />
                  {item.customer && <Badge label={item.customer} />}
                </div>
                <p className="text-sm font-semibold text-ink">{item.title}</p>
                <p className="text-xs text-sub">{item.description}</p>
                {item.reason && <p className="text-xs text-gray-500 mt-1">Why: {item.reason}</p>}
                {item.related_state && <p className="text-xs text-gray-400 mt-0.5">State: {item.related_state}</p>}
                {item.trace_id && (
                  <Link href={`/debug?trace=${item.trace_id}`} className="text-xs text-blue-500 hover:underline mt-2 inline-block">
                    View Trace
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </Card>

        <div className="space-y-4">
          {displayAlerts.map((item) => (
            <Alert key={item.id} title={item.title} message={item.message} level={item.level as "high" | "medium"} />
          ))}
          <ActionPanel
            title="AI Summary"
            items={[
              {
                label: "Used Data",
                value: usedRealData ? "Real ProjectAggregate API" : (homeData.data_sources?.join(", ") || "Sales trend, task logs, project timeline")
              },
              { label: "Data Source", value: usedRealData ? "Live" : "Fallback" },
              { label: "Next Action", value: "Review today's urgent cases" },
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
