import { Card, EmptyState, SectionHeader, StatusBadge } from "@/components/design-system";
import { executionHistory } from "@/lib/mock-data";

export default function HistoryPage() {
  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">History</h1>
        <p className="page-subtitle">Execution, generated artifacts, approval, and feedback records.</p>
      </header>

      <Card>
        <SectionHeader title="AI Execution History" subtitle="Recent generated outputs and decision records." />
        <ul className="space-y-2 text-sm">
          {executionHistory.map((item) => (
            <li key={item.id} className="surface-soft p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="font-medium">{item.title}</div>
                <StatusBadge status={item.status} />
              </div>
              <div className="text-xs text-sub">{item.type} | {item.at}</div>
            </li>
          ))}
        </ul>
      </Card>

      <EmptyState title="Feedback Queue (V0.2)" description="Users will be able to submit accepted/rejected and corrected output feedback in the next version." />
    </div>
  );
}
