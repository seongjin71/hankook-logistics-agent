const BASE = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

/* ── Dashboard ── */
export const fetchOverview = () =>
  request<Record<string, unknown>>("/api/dashboard/overview");

/* ── Orders ── */
export const fetchOrders = (params?: Record<string, string>) => {
  const q = params ? "?" + new URLSearchParams(params).toString() : "";
  return request<Record<string, unknown>>(`/api/orders${q}`);
};

/* ── Agent Events ── */
export const fetchAgentEvents = (params?: Record<string, string>) => {
  const q = params ? "?" + new URLSearchParams(params).toString() : "";
  return request<Record<string, unknown>>(`/api/agents/events${q}`);
};

export const fetchTimeline = (minutes = 30) =>
  request<Record<string, unknown>>(`/api/agents/timeline?minutes=${minutes}`);

/* ── Actions ── */
export const fetchPendingActions = () =>
  request<Record<string, unknown>>("/api/actions/pending");

export const approveAction = (eventId: string) =>
  request<Record<string, unknown>>(`/api/actions/${eventId}/approve`, {
    method: "POST",
  });

export const rejectAction = (eventId: string, reason: string) =>
  request<Record<string, unknown>>(`/api/actions/${eventId}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });

/* ── Simulation ── */
export const setSimSpeed = (speed: number) =>
  request<Record<string, unknown>>("/api/simulation/speed", {
    method: "PUT",
    body: JSON.stringify({ speed }),
  });

export const triggerAnomaly = (scenario: string) =>
  request<Record<string, unknown>>("/api/simulation/trigger-anomaly", {
    method: "POST",
    body: JSON.stringify({ scenario }),
  });

/* ── Demo ── */
export const startDemo = () =>
  request<Record<string, unknown>>("/api/simulation/start-demo", {
    method: "POST",
  });

export const getDemoStatus = () =>
  request<Record<string, unknown>>("/api/simulation/demo-status");

export const stopDemo = () =>
  request<Record<string, unknown>>("/api/simulation/stop-demo", {
    method: "POST",
  });

export const resetSimulation = () =>
  request<Record<string, unknown>>("/api/simulation/reset", {
    method: "POST",
  });

/* ── Health ── */
export const fetchHealth = () =>
  request<Record<string, unknown>>("/api/health");
