"use client";

import { useSearchParams } from "next/navigation";
import { Card, SectionHeader } from "@/components/design-system";
import { debugTrace } from "@/lib/mock-data";
import { getDebugTrace, getProjectTrace } from "@/lib/api-client";
import { useEffect, useState } from "react";

interface TraceData {
  trace_id?: string;
  project_id?: string;
  po_number?: string;
  events?: any;
  state_determination?: any;
  goal_evaluations?: any;
  decisions?: any;
  actions?: any;
  data_sources?: any;
}

export default function DebugPage() {
  const searchParams = useSearchParams();
  const traceId = searchParams?.get("trace");
  const projectId = searchParams?.get("project");

  const [traceData, setTraceData] = useState<TraceData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTrace() {
      if (!traceId && !projectId) {
        setTraceData(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        let response;
        if (projectId) {
          response = await getProjectTrace(projectId);
          if (response.success && response.trace) {
            setTraceData(response.trace);
          } else {
            throw new Error("Failed to load project trace");
          }
        } else if (traceId) {
          response = await getDebugTrace(traceId);
          if (response.success && response.trace) {
            setTraceData(response.trace);
          } else {
            throw new Error("Failed to load debug trace");
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        setTraceData(null);
      } finally {
        setIsLoading(false);
      }
    }

    loadTrace();
  }, [traceId, projectId]);

  const displayTrace = traceData || debugTrace;

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="page-title">判断理由</h1>
            <p className="page-subtitle">Developer/Admin only detailed runtime visibility.</p>
            {traceId && <p className="text-xs text-blue-600 mt-2">Trace ID: {traceId}</p>}
            {projectId && <p className="text-xs text-blue-600 mt-2">Project ID: {projectId}</p>}
            {error && <p className="text-xs text-red-600 mt-2">Error: {error}</p>}
            {isLoading && <p className="text-xs text-gray-500 mt-2">Loading trace...</p>}
          </div>
        </div>
      </header>

      {isLoading && (
        <Card>
          <p className="text-center py-8 text-gray-500">Loading trace data...</p>
        </Card>
      )}

      {!isLoading && displayTrace && (
        <div className="grid gap-4 lg:grid-cols-2">
          {traceData?.events && (
            <Card>
              <SectionHeader title="Business Events" />
              <pre className="overflow-auto text-xs bg-gray-50 p-3 rounded max-h-96">
                {JSON.stringify(traceData.events, null, 2)}
              </pre>
            </Card>
          )}

          {traceData?.state_determination && (
            <Card>
              <SectionHeader title="State Determination" />
              <pre className="overflow-auto text-xs bg-gray-50 p-3 rounded max-h-96">
                {JSON.stringify(traceData.state_determination, null, 2)}
              </pre>
            </Card>
          )}

          {traceData?.goal_evaluations && (
            <Card>
              <SectionHeader title="Goal Evaluations" />
              <pre className="overflow-auto text-xs bg-gray-50 p-3 rounded max-h-96">
                {JSON.stringify(traceData.goal_evaluations, null, 2)}
              </pre>
            </Card>
          )}

          {traceData?.decisions && (
            <Card>
              <SectionHeader title="Decisions" />
              <pre className="overflow-auto text-xs bg-gray-50 p-3 rounded max-h-96">
                {JSON.stringify(traceData.decisions, null, 2)}
              </pre>
            </Card>
          )}

          {traceData?.actions && (
            <Card>
              <SectionHeader title="Actions" />
              <pre className="overflow-auto text-xs bg-gray-50 p-3 rounded max-h-96">
                {JSON.stringify(traceData.actions, null, 2)}
              </pre>
            </Card>
          )}

          {traceData?.data_sources && (
            <Card>
              <SectionHeader title="Data Sources" />
              <pre className="overflow-auto text-xs bg-gray-50 p-3 rounded max-h-96">
                {JSON.stringify(traceData.data_sources, null, 2)}
              </pre>
            </Card>
          )}

          {!traceData && (
            <>
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
            </>
          )}
        </div>
      )}
    </div>
  );
}

