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
    return { success: true, data };
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
