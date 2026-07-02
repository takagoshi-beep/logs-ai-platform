/**
 * API Client - handles all backend communication
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

interface ApiResponse<T = any> {
  success?: boolean;
  error?: string;
  data?: T;
  [key: string]: any;
}

/**
 * Generic API call handler with error handling
 */
async function apiCall<T = any>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`API call failed: ${endpoint}`, error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

/**
 * Get home page payload with today's actions and KPIs
 */
export async function getHome() {
  return apiCall("/api/home");
}

/**
 * Get task recommendations
 */
export async function getTaskRecommendations() {
  return apiCall("/api/tasks/recommend", {
    method: "POST",
  });
}

/**
 * Get execution history
 */
export async function getExecutionHistory() {
  return apiCall("/api/history");
}

/**
 * Get debug trace for a given trace ID
 */
export async function getDebugTrace(traceId: string) {
  return apiCall(`/api/debug/trace/${traceId}`);
}

/**
 * Store a product event
 */
export async function storeProductEvent(event: {
  event_type: string;
  page: string;
  action: string;
  metadata?: Record<string, any>;
}) {
  return apiCall("/api/events", {
    method: "POST",
    body: JSON.stringify(event),
  });
}

/**
 * Get list of project candidates
 */
export async function getProjects(limit: number = 10) {
  return apiCall("/api/projects", {
    method: "GET",
  });
}

/**
 * Ask a consultation question and get an evidence-backed answer
 */
export async function consultQuestion(message: string) {
  return apiCall("/api/chat", {
    method: "POST",
    body: JSON.stringify({ user_id: "u-demo", role: "sales", message }),
  });
}

/**
 * Run the Reasoning Pipeline v0.1: Intent / Meaning / Knowledge Used / Required Data / Unknown
 */
export async function runReasoning(message: string) {
  return apiCall("/api/reasoning", {
    method: "POST",
    body: JSON.stringify({ user_id: "u-demo", role: "sales", message }),
  });
}

/**
 * Get single project with full aggregate
 */
export async function getProject(projectId: string) {
  return apiCall(`/api/projects/${projectId}`);
}

/**
 * Get project trace (Event → State → Goal → Decision → Action)
 */
export async function getProjectTrace(projectId: string) {
  return apiCall(`/api/projects/${projectId}/trace`);
}

/**
 * Get today's actions from all projects
 */
export async function getTodayActions(limit: number = 20) {
  return apiCall(`/api/today-actions?limit=${limit}`);
}

/**
 * Get the Learning Center aggregate payload (Operational, Governed,
 * Approval Queue, Policy Memory, Activity) — Blueprint v0.2 §8.11
 */
export async function getLearningCenter() {
  return apiCall("/api/learning/center");
}

/**
 * Submit a Governance decision (approve/reject) on a queued Learning Candidate
 */
export async function reviewLearningApproval(
  approvalId: string,
  decision: "APPROVED" | "REJECTED",
  approverId: string,
  reason: string
) {
  return apiCall(`/api/learning/approval-queue/${approvalId}/review`, {
    method: "POST",
    body: JSON.stringify({ decision, approver_id: approverId, reason }),
  });
}

/**
 * Create a new OEM project
 */
export async function createProject(project: {
  customer_name: string;
  project_title: string;
  po_number: string;
  po_amount: string | number;
  required_delivery_date: string;
}) {
  return apiCall("/api/projects", {
    method: "POST",
    body: JSON.stringify(project),
  });
}

/**
 * Submit feedback on a suggested action for a project
 */
export async function projectFeedback(
  projectId: string,
  feedback: {
    action_id: string;
    feedback_text: string;
    helpful: boolean;
  }
) {
  return apiCall(`/api/projects/${projectId}/feedback`, {
    method: "POST",
    body: JSON.stringify(feedback),
  });
}
