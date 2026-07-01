"use client";

import { useEffect, useState } from "react";
import { Badge, Card, SectionHeader } from "@/components/design-system";
import { getLearningCenter, reviewLearningApproval } from "@/lib/api-client";

interface LearningCandidate {
  id: string;
  title: string;
  description: string;
  source_type: string;
  learning_type: string;
  scope_type: string | null;
  scope_id: string | null;
  status: string;
  confidence: number;
  suggested_application: string;
  created_at: string;
}

interface ApprovalQueueEntry {
  approval_id: string;
  candidate_id: string;
  status: string;
  decision: string | null;
  approver_id: string | null;
  approval_reason: string | null;
  created_at: string;
}

interface PolicyMemoryEntry {
  policy_id: string;
  candidate_id: string;
  version: number;
  rule_definition: string;
  approved_by: string;
  active: boolean;
  approved_at: string;
}

interface ActivityEntry {
  id: string;
  event: string;
  candidate_id: string;
  summary: string;
  created_at: string;
}

interface LearningCenterData {
  operational: LearningCandidate[];
  governed: LearningCandidate[];
  approval_queue: ApprovalQueueEntry[];
  policy_memory: PolicyMemoryEntry[];
  activity: ActivityEntry[];
}

const TABS = [
  { key: "operational", label: "Operational Learning" },
  { key: "governed", label: "Governed Learning" },
  { key: "approval_queue", label: "Approval Queue" },
  { key: "policy_memory", label: "Policy Memory" },
  { key: "activity", label: "Activity" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

const EMPTY_DATA: LearningCenterData = {
  operational: [],
  governed: [],
  approval_queue: [],
  policy_memory: [],
  activity: [],
};

export default function LearningCenterPage() {
  const [data, setData] = useState<LearningCenterData>(EMPTY_DATA);
  const [activeTab, setActiveTab] = useState<TabKey>("operational");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getLearningCenter();
      if (response.success === false) {
        throw new Error(response.error || "Failed to load Learning Center");
      }
      setData({
        operational: response.operational || [],
        governed: response.governed || [],
        approval_queue: response.approval_queue || [],
        policy_memory: response.policy_memory || [],
        activity: response.activity || [],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setData(EMPTY_DATA);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleReview(approvalId: string, decision: "APPROVED" | "REJECTED") {
    await reviewLearningApproval(approvalId, decision, "ui-admin", `Reviewed via Learning Center (${decision})`);
    load();
  }

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">Learning Center</h1>
        <p className="page-subtitle">
          Operational and Governed Learning, Governance Approval Queue, Policy Memory, and Activity — Blueprint v0.2 Ch.8.
        </p>
        {error && <p className="text-xs text-red-600 mt-2">Error: {error}</p>}
        {isLoading && <p className="text-xs text-gray-500 mt-2">Loading...</p>}
      </header>

      <div className="flex gap-2 flex-wrap">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
              activeTab === tab.key ? "bg-accent text-white" : "bg-white border border-slate-200 text-ink hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "operational" && (
        <Card>
          <SectionHeader title="Operational Learning" subtitle="Applied automatically to scoped memory, no approval needed." />
          <div className="mt-4 space-y-3">
            {data.operational.map((c) => (
              <CandidateRow key={c.id} candidate={c} />
            ))}
            {data.operational.length === 0 && !isLoading && <Empty label="No operational learning candidates yet." />}
          </div>
        </Card>
      )}

      {activeTab === "governed" && (
        <Card>
          <SectionHeader title="Governed Learning" subtitle="Requires Governance approval before becoming a policy rule." />
          <div className="mt-4 space-y-3">
            {data.governed.map((c) => (
              <CandidateRow key={c.id} candidate={c} />
            ))}
            {data.governed.length === 0 && !isLoading && <Empty label="No governed learning candidates yet." />}
          </div>
        </Card>
      )}

      {activeTab === "approval_queue" && (
        <Card>
          <SectionHeader title="Approval Queue" subtitle="Admin review of Governed Learning Candidates." />
          <div className="mt-4 space-y-3">
            {data.approval_queue.map((entry) => (
              <div key={entry.approval_id} className="surface-soft p-4 rounded-lg border border-slate-200">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-gray-500">{entry.approval_id}</p>
                  <Badge label={entry.status} tone={entry.status === "PENDING" ? "medium" : entry.status === "APPROVED" ? "success" : "high"} />
                </div>
                <p className="text-sm mt-1">Candidate: {entry.candidate_id}</p>
                {entry.approval_reason && <p className="text-xs text-gray-600 mt-1">{entry.approval_reason}</p>}
                {entry.status === "PENDING" && (
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => handleReview(entry.approval_id, "APPROVED")}
                      className="rounded-lg bg-accent text-white px-3 py-1.5 text-xs font-medium hover:bg-teal-700"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleReview(entry.approval_id, "REJECTED")}
                      className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-ink hover:bg-slate-50"
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
            {data.approval_queue.length === 0 && !isLoading && <Empty label="No items in the Approval Queue." />}
          </div>
        </Card>
      )}

      {activeTab === "policy_memory" && (
        <Card>
          <SectionHeader title="Policy Memory" subtitle="Approved rules currently active or historical." />
          <div className="mt-4 space-y-3">
            {data.policy_memory.map((p) => (
              <div key={p.policy_id} className="surface-soft p-4 rounded-lg border border-slate-200">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold">{p.policy_id} (v{p.version})</p>
                  <Badge label={p.active ? "active" : "inactive"} tone={p.active ? "success" : "default"} />
                </div>
                <p className="text-xs text-gray-600 mt-1">{p.rule_definition}</p>
                <p className="text-xs text-gray-500 mt-1">Approved by {p.approved_by}</p>
              </div>
            ))}
            {data.policy_memory.length === 0 && !isLoading && <Empty label="No policies approved yet." />}
          </div>
        </Card>
      )}

      {activeTab === "activity" && (
        <Card>
          <SectionHeader title="Activity" subtitle="What Learning observed, applied, and queued — in plain English." />
          <div className="mt-4 space-y-2">
            {data.activity.map((a) => (
              <div key={a.id} className="text-sm border-b border-slate-100 pb-2">
                <span className="text-xs text-gray-500 mr-2">{new Date(a.created_at).toLocaleString()}</span>
                {a.summary}
              </div>
            ))}
            {data.activity.length === 0 && !isLoading && <Empty label="No learning activity recorded yet." />}
          </div>
        </Card>
      )}
    </div>
  );
}

function CandidateRow({ candidate }: { candidate: LearningCandidate }) {
  return (
    <div className="surface-soft p-4 rounded-lg border border-slate-200">
      <div className="flex items-start justify-between">
        <p className="font-semibold text-sm">{candidate.title}</p>
        <Badge label={candidate.status} tone={candidate.status === "applied" ? "success" : "default"} />
      </div>
      <p className="text-xs text-gray-600 mt-1">{candidate.description}</p>
      <div className="flex gap-2 flex-wrap mt-2">
        <Badge label={`source: ${candidate.source_type}`} />
        {candidate.scope_type && <Badge label={`scope: ${candidate.scope_type}${candidate.scope_id ? `:${candidate.scope_id}` : ""}`} />}
        <Badge label={`confidence: ${candidate.confidence.toFixed(2)}`} />
      </div>
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return <p className="text-center py-8 text-gray-500 text-sm">{label}</p>;
}
