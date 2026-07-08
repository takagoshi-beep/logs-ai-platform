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
      credentials: "include",
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
export async function consultQuestion(message: string, sessionId?: string) {
  return apiCall("/api/chat", {
    method: "POST",
    body: JSON.stringify({ user_id: "u-demo", role: "sales", message, session_id: sessionId }),
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
 * Build the download URL for a generated proposal image.
 */
export function getProposalImageUrl(traceId: string) {
  return `${API_BASE}/api/proposals/images/${traceId}/download`;
}

/**
 * Generate a proposal draft (LLM-backed text, optional web search / image).
 * The draft is NOT sendable until approved via Governance
 * (see /governance/{id}/decide) — this only returns the draft + its
 * approval status.
 */
export async function draftProposal(
  customer: string,
  purpose: string,
  includeExternal: boolean = false,
  includeImage: boolean = false
) {
  return apiCall("/api/proposals/draft", {
    method: "POST",
    body: JSON.stringify({
      user_id: "u-demo",
      role: "sales",
      customer,
      purpose,
      include_external: includeExternal,
      include_image: includeImage,
    }),
  });
}
/**
 * Upload a document format template (see docs/architecture.md 13/14 for
 * `/document-formats`). File type is intentionally not restricted
 * client-side; the backend currently only supports Excel (.xlsx/.xlsm)
 * and returns a clear error for anything else, so widening supported
 * formats later needs no frontend change.
 *
 * Uses a raw `fetch` (not the shared `apiCall` helper) because file
 * uploads need `multipart/form-data`, which the browser sets correctly
 * on its own — manually setting Content-Type here would break the
 * multipart boundary.
 *
 * NOTE: this router is mounted WITHOUT the `/api` prefix (unlike most
 * other endpoints) — see `backend/main.py`. Do not add `/api` here.
 */
export async function uploadDocumentFormat(name: string, file: File) {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("file", file);
  try {
    const response = await fetch(`${API_BASE}/document-formats`, {
      method: "POST",
      credentials: "include",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `API Error: ${response.status}`);
    }
    return data;
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "アップロードに失敗しました",
    };
  }
}

/**
 * List all registered document formats, with live-resolved Governance
 * approval status.
 */
export async function listDocumentFormats() {
  return apiCall("/document-formats");
}

/**
 * Generate a filled document from an APPROVED format. `userData` is
 * merged with real internal project data (if `projectId` is given),
 * with `userData` taking precedence on overlap. `tableRows` (2026-07-06)
 * fills repeating detail-table sections: {table_id: [{field_name: value,
 * ...}, ...]}, one entry per row, written starting directly below that
 * table's header row.
 */
export async function generateDocument(
  formatId: string,
  projectId: string,
  userData: Record<string, any>,
  tableRows: Record<string, Array<Record<string, any>>> = {}
) {
  return apiCall(`/document-formats/${formatId}/generate`, {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, user_data: userData, table_rows: tableRows }),
  });
}

/**
 * Build the download URL for a generated document.
 */
export function getGeneratedDocumentUrl(outputId: string) {
  return `${API_BASE}/document-formats/generated/${outputId}/download`;
}

/**
 * Approve or reject a Governance queue item (e.g. a document format's
 * structure inference). This calls the same endpoint that was previously
 * only reachable via `/governance/queue` outside the app — wiring it
 * into the UI lets a user complete the upload→approve→generate flow
 * without leaving the page. Requires admin role (14.22) — the approver
 * identity comes from the server-side session, not this call.
 */
export async function decideGovernance(
  approvalId: string,
  decision: "APPROVED" | "REJECTED",
  reason: string
) {
  return apiCall(`/governance/${approvalId}/decide`, {
    method: "POST",
    body: JSON.stringify({ decision, reason }),
  });
}

/**
 * Let a human edit the AI-detected field mappings before confirming a
 * format (rename a field, fix which cell it points to, or remove a false
 * positive) — step 2 of the upload -> agree on structure together -> use
 * flow.
 */
export async function updateFieldMappings(
  formatId: string,
  fieldMappings: Array<Record<string, any>>
) {
  return apiCall(`/document-formats/${formatId}/field-mappings`, {
    method: "PUT",
    body: JSON.stringify({ field_mappings: fieldMappings }),
  });
}

/**
 * Parse a free-text chat instruction (e.g. "顧客名はUS_LOGS Inc.、数量は
 * 50個") into values for a confirmed format's single-value fields. Only
 * pre-fills the generation form — the human still reviews/edits before
 * generating.
 */
export async function parseInstruction(formatId: string, instruction: string) {
  return apiCall(`/document-formats/${formatId}/parse-instruction`, {
    method: "POST",
    body: JSON.stringify({ instruction }),
  });
}

export async function getProject(projectId: string) {
  return apiCall(`/api/projects/${projectId}`);
}

/**
 * Get products related to the logged-in user (docs/architecture.md 14.30)
 */
export async function getProducts(limit: number = 20, scope: "mine" | "all" = "mine") {
  return apiCall(`/api/products?limit=${limit}&scope=${scope}`);
}

/**
 * Get full cross-referenced detail for a single product (PO/sales/purchases/samples)
 */
export async function getProduct(logsCode: string) {
  return apiCall(`/api/products/${logsCode}`);
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
  reason: string
) {
  return apiCall(`/api/learning/approval-queue/${approvalId}/review`, {
    method: "POST",
    body: JSON.stringify({ decision, reason }),
  });
}

/**
 * Get current logged-in user (14.22)
 */
export async function getCurrentUser() {
  return apiCall("/api/auth/me");
}

/**
 * Log in with a Google Identity Services ID token (14.22)
 */
export async function loginWithGoogle(credential: string) {
  return apiCall("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ credential }),
  });
}

/**
 * Log out (clears the session cookie) (14.22)
 */
export async function logout() {
  return apiCall("/api/auth/logout", { method: "POST" });
}