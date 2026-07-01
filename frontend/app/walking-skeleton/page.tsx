"use client";

import { useEffect, useState } from "react";
import { Badge, Card, SectionHeader, Button } from "@/components/design-system";
import { createProject, getProject, projectFeedback, getLearningCenter, getDebugTrace } from "@/lib/api-client";

interface ProjectAggregate {
  project_id: string;
  state: string;
  data?: {
    project_title: string;
    customer_name: string;
    po_amount: number;
    po_number: string;
  };
  goal_evaluations?: {
    evaluations: Array<{ goal: string; status: string; reason: string }>;
  };
  actions?: Array<{ action_id: string; title: string; priority: string; reason: string }>;
  events?: Array<{ event_type: string; event_time: string; business_meaning: string }>;
  trace_id?: string;
}

interface LearningData {
  operational: any[];
  governed: any[];
  approval_queue: any[];
  policy_memory: any[];
  activity: any[];
}

export default function WalkingSkeletonPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectAggregate | null>(null);
  const [learningData, setLearningData] = useState<LearningData | null>(null);
  const [traceData, setTraceData] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(true);
  const [newProjectForm, setNewProjectForm] = useState({
    customer_name: "Fanatics OEM",
    project_title: "Custom Integration Project",
    po_number: "PO-2026-001",
    po_amount: "50000",
    required_delivery_date: "2026-08-15",
  });

  async function handleCreateProject() {
    setIsLoading(true);
    setError(null);
    try {
      const result = await createProject(newProjectForm);
      if (result.success && result.project_id) {
        setProjectId(result.project_id);
        setProject(result.aggregate);
        setShowCreateForm(false);

        // Fetch learning data
        const learning = await getLearningCenter();
        if (learning.success) {
          setLearningData(learning as LearningData);
        }

        // Fetch trace if available
        if (result.aggregate.trace_id) {
          const trace = await getDebugTrace(result.aggregate.trace_id);
          if (trace.success) {
            setTraceData(trace.data);
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleProjectFeedback(actionId: string, helpful: boolean) {
    if (!projectId) return;

    setIsLoading(true);
    setError(null);
    try {
      const result = await projectFeedback(projectId, {
        action_id: actionId,
        feedback_text: `User marked action as ${helpful ? "helpful" : "not helpful"}`,
        helpful,
      });

      if (result.success) {
        // Refresh learning data
        const learning = await getLearningCenter();
        if (learning.success) {
          setLearningData(learning as LearningData);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit feedback");
    } finally {
      setIsLoading(false);
    }
  }

  const statusTone = (status: string) => {
    if (status.includes("OVERDUE") || status.includes("FAILED")) return "high";
    if (status.includes("RISK") || status.includes("AT_RISK")) return "medium";
    if (status.includes("COMPLETED") || status.includes("ACHIEVED")) return "success";
    return "default";
  };

  const goalStatusTone = (status: string) => {
    if (status === "ACHIEVED") return "success";
    if (status === "FAILED") return "high";
    if (status === "AT_RISK") return "medium";
    return "default";
  };

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">Walking Skeleton Demo</h1>
        <p className="page-subtitle">
          End-to-end flow: Project → Understanding → Execution → Learning → Governance → Activity → Trace
        </p>
        {error && <p className="text-xs text-red-600 mt-2">Error: {error}</p>}
      </header>

      {showCreateForm ? (
        <Card>
          <SectionHeader title="Create OEM Project" subtitle="Start the Walking Skeleton flow" />
          <div className="mt-4 space-y-3">
            <div>
              <label className="text-xs font-semibold text-ink">Customer Name</label>
              <input
                type="text"
                value={newProjectForm.customer_name}
                onChange={(e) => setNewProjectForm({ ...newProjectForm, customer_name: e.target.value })}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                disabled={isLoading}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-ink">Project Title</label>
              <input
                type="text"
                value={newProjectForm.project_title}
                onChange={(e) => setNewProjectForm({ ...newProjectForm, project_title: e.target.value })}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                disabled={isLoading}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-ink">PO Number</label>
              <input
                type="text"
                value={newProjectForm.po_number}
                onChange={(e) => setNewProjectForm({ ...newProjectForm, po_number: e.target.value })}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                disabled={isLoading}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-ink">PO Amount</label>
              <input
                type="number"
                value={newProjectForm.po_amount}
                onChange={(e) => setNewProjectForm({ ...newProjectForm, po_amount: e.target.value })}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                disabled={isLoading}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-ink">Required Delivery Date</label>
              <input
                type="date"
                value={newProjectForm.required_delivery_date}
                onChange={(e) => setNewProjectForm({ ...newProjectForm, required_delivery_date: e.target.value })}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                disabled={isLoading}
              />
            </div>
            <button
              onClick={handleCreateProject}
              disabled={isLoading}
              className="mt-3 w-full rounded-lg bg-accent text-white px-3 py-2 text-sm font-medium hover:bg-teal-700 disabled:opacity-50"
            >
              {isLoading ? "Creating..." : "Create Project"}
            </button>
          </div>
        </Card>
      ) : project ? (
        <>
          {/* Project Summary */}
          <Card>
            <SectionHeader title="Project Summary" subtitle={`ID: ${projectId}`} />
            <div className="mt-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-sub">Title:</span>
                <span className="text-sm font-semibold">{project.data?.project_title}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-sub">Customer:</span>
                <span className="text-sm font-semibold">{project.data?.customer_name}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-sub">State:</span>
                <Badge label={project.state} tone={statusTone(project.state)} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-sub">Amount:</span>
                <span className="text-sm font-semibold">${project.data?.po_amount || 0}</span>
              </div>
            </div>
          </Card>

          {/* Project Understanding */}
          <div className="grid gap-5 lg:grid-cols-2">
            {/* Goals */}
            <Card>
              <SectionHeader title="Goals" subtitle="Business objectives and status" />
              <div className="mt-4 space-y-2">
                {project.goal_evaluations?.evaluations?.map((goal: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
                    <span className="text-sm">{goal.goal}</span>
                    <Badge label={goal.status} tone={goalStatusTone(goal.status)} />
                  </div>
                )) || <p className="text-xs text-gray-500">No goals evaluated</p>}
              </div>
            </Card>

            {/* Recent Events */}
            <Card>
              <SectionHeader title="Recent Events" subtitle="What happened" />
              <div className="mt-4 space-y-2">
                {project.events?.slice(0, 5)?.map((event: any, idx: number) => (
                  <div key={idx} className="border-b border-slate-100 pb-2 last:border-0">
                    <p className="text-xs font-semibold text-ink">{event.event_type}</p>
                    <p className="text-xs text-sub">{event.business_meaning}</p>
                  </div>
                )) || <p className="text-xs text-gray-500">No events</p>}
              </div>
            </Card>
          </div>

          {/* Business Execution - Next Actions */}
          <Card>
            <SectionHeader title="Suggested Next Actions" subtitle="AI recommendations for project execution" />
            <div className="mt-4 space-y-3">
              {project.actions?.slice(0, 5)?.map((action: any) => (
                <div key={action.action_id} className="surface-soft p-4 rounded-lg border border-slate-200">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-semibold">{action.title}</p>
                      <p className="text-xs text-gray-600 mt-1">{action.reason}</p>
                    </div>
                    <Badge label={action.priority} tone={action.priority === "high" ? "high" : "medium"} />
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => handleProjectFeedback(action.action_id, true)}
                      disabled={isLoading}
                      className="rounded text-xs px-2 py-1 bg-green-50 text-green-700 hover:bg-green-100 disabled:opacity-50"
                    >
                      Helpful
                    </button>
                    <button
                      onClick={() => handleProjectFeedback(action.action_id, false)}
                      disabled={isLoading}
                      className="rounded text-xs px-2 py-1 bg-red-50 text-red-700 hover:bg-red-100 disabled:opacity-50"
                    >
                      Not Helpful
                    </button>
                  </div>
                </div>
              )) || <p className="text-xs text-gray-500">No suggested actions</p>}
            </div>
          </Card>

          {/* Learning Activity Feed */}
          {learningData && (
            <Card>
              <SectionHeader title="Learning Activity Flow" subtitle="Candidates, classifications, approvals" />
              <div className="mt-4 space-y-3">
                <div className="text-xs">
                  <div className="p-2 bg-blue-50 rounded mb-2">
                    <span className="font-semibold text-blue-900">Operational Learning: </span>
                    <span className="text-blue-800">{learningData.operational?.length || 0} candidates</span>
                  </div>
                  <div className="p-2 bg-yellow-50 rounded mb-2">
                    <span className="font-semibold text-yellow-900">Governed Learning: </span>
                    <span className="text-yellow-800">{learningData.governed?.length || 0} candidates</span>
                  </div>
                  <div className="p-2 bg-purple-50 rounded mb-2">
                    <span className="font-semibold text-purple-900">Approval Queue: </span>
                    <span className="text-purple-800">{learningData.approval_queue?.length || 0} pending</span>
                  </div>
                  <div className="p-2 bg-green-50 rounded">
                    <span className="font-semibold text-green-900">Approved Policies: </span>
                    <span className="text-green-800">{learningData.policy_memory?.length || 0} policies</span>
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold mb-2">Activity Feed</p>
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {learningData.activity?.map((entry: any, idx: number) => (
                      <div key={idx} className="text-xs border-l-2 border-slate-300 pl-2 py-1">
                        <span className="text-gray-500">{new Date(entry.created_at).toLocaleTimeString()}</span>
                        <p className="text-sm mt-0.5">{entry.summary}</p>
                      </div>
                    )) || <p className="text-xs text-gray-500">No activity yet</p>}
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Debug Trace */}
          {traceData && (
            <Card>
              <SectionHeader title="Debug Trace" subtitle={`Trace ID: ${project.trace_id}`} />
              <div className="mt-4">
                <details className="cursor-pointer">
                  <summary className="text-sm font-semibold text-accent hover:underline">
                    Show Full Trace Details
                  </summary>
                  <div className="mt-3 p-3 bg-slate-50 rounded text-xs font-mono overflow-auto max-h-32">
                    <pre>{JSON.stringify(traceData, null, 2)}</pre>
                  </div>
                </details>
              </div>
            </Card>
          )}

          {/* Reset Button */}
          <div className="flex justify-center pt-4">
            <button
              onClick={() => {
                setShowCreateForm(true);
                setProjectId(null);
                setProject(null);
                setLearningData(null);
                setTraceData(null);
              }}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-ink hover:bg-slate-50"
            >
              Create Another Project
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
}
