import { Card, SectionHeader } from "@/components/design-system";
import { debugTrace } from "@/lib/mock-data";

export default function DebugPage() {
  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">Debug Trace Panel</h1>
        <p className="page-subtitle">Developer/Admin only detailed runtime visibility.</p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionHeader title="Intent and Meaning" />
          <pre className="overflow-auto text-xs">{JSON.stringify({ intent: debugTrace.intent, meaning: debugTrace.meaning }, null, 2)}</pre>
        </Card>

        <Card>
          <SectionHeader title="Knowledge and Memory Trace" />
          <pre className="overflow-auto text-xs">{JSON.stringify({ knowledge: debugTrace.knowledge, memory: debugTrace.memory }, null, 2)}</pre>
        </Card>

        <Card>
          <SectionHeader title="Capability and Validation" />
          <pre className="overflow-auto text-xs">{JSON.stringify({ capability: debugTrace.capability, validation: debugTrace.validation }, null, 2)}</pre>
        </Card>

        <Card>
          <SectionHeader title="Evaluation and Runtime Logs" />
          <pre className="overflow-auto text-xs">{JSON.stringify({ evaluation: debugTrace.evaluation, runtimeLogs: debugTrace.runtimeLogs }, null, 2)}</pre>
        </Card>
      </div>
    </div>
  );
}
