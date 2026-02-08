export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatNumber(n: number): string {
  return n.toLocaleString("ko-KR");
}

export function formatPercent(n: number, decimals = 1): string {
  return `${(n * 100).toFixed(decimals)}%`;
}

export function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}초 전`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}분 전`;
  const hr = Math.floor(min / 60);
  return `${hr}시간 전`;
}

export function severityColor(sev: string): string {
  switch (sev) {
    case "CRITICAL":
      return "text-critical";
    case "WARNING":
      return "text-warning";
    default:
      return "text-info";
  }
}

export function severityBg(sev: string): string {
  switch (sev) {
    case "CRITICAL":
      return "bg-critical/10 text-critical";
    case "WARNING":
      return "bg-warning/10 text-warning";
    default:
      return "bg-info/10 text-info";
  }
}

export function agentColor(agent: string): string {
  switch (agent) {
    case "MONITOR":
      return "#6366F1";
    case "ANOMALY":
      return "#EC4899";
    case "PRIORITY":
      return "#F59E0B";
    case "ACTION":
      return "#10B981";
    default:
      return "#94a3b8";
  }
}

export function executionModeBadge(mode: string): {
  label: string;
  className: string;
} {
  switch (mode) {
    case "AUTO":
      return { label: "Auto", className: "bg-success/15 text-success" };
    case "HUMAN_APPROVED":
      return { label: "Approved", className: "bg-info/15 text-info" };
    case "PENDING_APPROVAL":
      return { label: "Pending", className: "bg-warning/15 text-warning" };
    case "ESCALATED":
      return { label: "Escalated", className: "bg-critical/15 text-critical" };
    default:
      return { label: mode, className: "bg-gray-100 text-gray-600" };
  }
}
