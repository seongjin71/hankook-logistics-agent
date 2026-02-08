import { Bell, AlertTriangle, AlertCircle, Info } from "lucide-react";
import type { TimelineEvent } from "../../types";
import { formatTime } from "../../utils/formatters";

interface Props {
  alerts: TimelineEvent[];
}

const SEVERITY_STYLE: Record<
  string,
  { icon: React.ReactNode; border: string; bg: string }
> = {
  CRITICAL: {
    icon: <AlertCircle size={14} className="text-critical" />,
    border: "border-l-critical",
    bg: "bg-critical/5 animate-pulse-critical",
  },
  WARNING: {
    icon: <AlertTriangle size={14} className="text-warning" />,
    border: "border-l-warning",
    bg: "",
  },
  INFO: {
    icon: <Info size={14} className="text-info" />,
    border: "border-l-info",
    bg: "",
  },
};

export default function AlertFeed({ alerts }: Props) {
  // Show only OBSERVE-phase events (anomaly detections) as alerts
  const filtered = alerts.filter(
    (a) => a.ooda_phase === "OBSERVE" || a.severity === "CRITICAL",
  );

  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Bell size={14} className="text-critical" />
        <h3 className="text-sm font-semibold text-dark">Alerts</h3>
        {filtered.length > 0 && (
          <span className="ml-auto bg-critical text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
            {filtered.length}
          </span>
        )}
      </div>

      <div className="space-y-2 max-h-[220px] overflow-y-auto">
        {filtered.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-3">
            No alerts
          </p>
        )}
        {filtered.map((a, i) => {
          const style = SEVERITY_STYLE[a.severity] ?? SEVERITY_STYLE.INFO;
          return (
            <div
              key={`${a.event_id}-${i}`}
              className={`border-l-3 rounded-r-lg p-2.5 animate-slide-in ${style.border} ${style.bg}`}
            >
              <div className="flex items-center gap-2">
                {style.icon}
                <span className="text-[10px] text-gray-400">
                  {formatTime(a.timestamp)}
                </span>
              </div>
              <p className="text-xs font-medium text-dark mt-1">{a.title}</p>
              <p className="text-[10px] text-gray-400">{a.event_type}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
