"use client";

import { useState } from "react";
import { ActionPanel, Button, Card, SectionHeader } from "@/components/design-system";

export default function ChatPage() {
  const [showTrace, setShowTrace] = useState(false);

  return (
    <div className="space-y-5">
      <header className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <h1 className="page-title">Chat</h1>
          <p className="page-subtitle">Chat is a feature for getting work done, not the starting point.</p>
        </div>
        <Button tone="ghost" size="sm" onClick={() => setShowTrace((v) => !v)}>
          Admin Trace Toggle
        </Button>
      </header>

      <Card>
        <SectionHeader title="Business AI Chat" subtitle="Use chat to decide concrete next steps." />
        <div className="space-y-3 text-sm">
          <div className="surface-soft p-3">User: Draft next actions for Fanatics delay risk.</div>
          <div className="rounded border border-teal-200 bg-teal-50 p-3">
            AI Response: 1) Confirm supplier ETA, 2) Reserve logistics slot, 3) Send stakeholder update.
          </div>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <ActionPanel
          title="Work Guidance"
          items={[
            { label: "Used Data", value: "Project FAN-204 history, communication memory, delay trend" },
            { label: "Confirmation", value: "Operations lead approval needed before send" },
            { label: "Next Action", value: "Create task batch and open workspace execution" },
          ]}
        />
        <Card>
          <SectionHeader title="Suggested Next Steps" />
          <ul className="mt-3 list-disc pl-5 text-sm">
            <li>Create task batch for owner assignment.</li>
            <li>Generate message draft for operations team.</li>
            <li>Open Workspace for execution details.</li>
          </ul>
        </Card>
      </div>

      {showTrace ? (
        <Card>
          <SectionHeader title="Trace (Developer/Admin)" subtitle="Only for admin/debug confirmation." />
          <pre className="overflow-auto text-xs">{JSON.stringify({ intent: "Monitoring", task: "required_action_check", validation: "pass" }, null, 2)}</pre>
        </Card>
      ) : null}
    </div>
  );
}
