import { ActionPanel, Badge, Button, Card, SectionHeader, StatusBadge, Timeline } from "@/components/design-system";
import { proposalDraft } from "@/lib/mock-data";

export default function ProposalBuilderPage() {
  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">Proposal Builder</h1>
        <p className="page-subtitle">Sales-ready flow from customer context to PowerPoint generation and review.</p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionHeader title="Customer and Proposal Goal" subtitle="Start with target customer and objective." />
          <div className="mt-4 space-y-3 text-sm">
            <div className="surface-soft p-3">Customer: {proposalDraft.customer}</div>
            <div className="surface-soft p-3">Purpose: {proposalDraft.purpose}</div>
            <div className="flex flex-wrap gap-2">
              <Button>Generate AI Structure</Button>
              <Button tone="ghost">Load Past Proposal</Button>
            </div>
          </div>
        </Card>

        <Card>
          <SectionHeader title="Reference Data" subtitle="Data sources used for narrative and proof." />
          <ul className="mt-4 space-y-2 text-sm">
            {proposalDraft.referenceData.map((item) => (
              <li key={item} className="surface-soft flex items-center justify-between p-3">
                <span>{item}</span>
                <Badge label="Included" tone="success" />
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Card>
          <SectionHeader title="AI Structure Draft" subtitle="Draft sections for proposal story construction." />
          <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm">
            {proposalDraft.outline.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <StatusBadge status={proposalDraft.reviewStatus} />
            <Badge label="PowerPoint ready" tone="medium" />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button>PowerPoint Generate</Button>
            <Button tone="ghost">Mark Review Complete</Button>
            <Button tone="neutral">Share to Workspace</Button>
          </div>
        </Card>

        <div className="space-y-4">
          <ActionPanel
            title="Next Action"
            items={[
              { label: "Review State", value: proposalDraft.reviewStatus },
              { label: "Next", value: proposalDraft.nextAction },
              { label: "Output", value: "PPTX draft + review notes" },
            ]}
          />
          <Card>
            <SectionHeader title="Review Timeline" />
            <div className="mt-3">
              <Timeline
                items={[
                  { id: "pt1", title: "Draft generated", time: "09:20", detail: "Outline from AI proposal planner." },
                  { id: "pt2", title: "Manager pre-check", time: "10:10", detail: "Margin section revision requested." },
                  { id: "pt3", title: "Ready for review", time: "11:05", detail: "Pending pptx export and send." },
                ]}
              />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
