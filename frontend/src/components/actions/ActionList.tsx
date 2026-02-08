import { CheckCircle, Shield, AlertOctagon } from "lucide-react";
import type { AgentEvent } from "../../types";
import { formatTime, executionModeBadge } from "../../utils/formatters";

interface Props {
  events: AgentEvent[];
}

const MODE_ICON: Record<string, React.ReactNode> = {
  AUTO: <CheckCircle size={12} className="text-success" />,
  HUMAN_APPROVED: <Shield size={12} className="text-info" />,
  ESCALATED: <AlertOctagon size={12} className="text-critical" />,
};

export default function ActionList({ events }: Props) {
  // Show only ACT-phase events that are not PENDING_APPROVAL
  const actions = events.filter(
    (e) =>
      e.ooda_phase === "ACT" &&
      e.execution_mode !== "PENDING_APPROVAL",
  );

  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-dark mb-3">Executed Actions</h3>
      <div className="space-y-2 max-h-[220px] overflow-y-auto">
        {actions.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-3">
            No executed actions
          </p>
        )}
        {actions.map((a) => {
          const badge = a.execution_mode
            ? executionModeBadge(a.execution_mode)
            : null;
          return (
            <div
              key={a.event_id}
              className="flex items-start gap-2 p-2 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="mt-0.5">
                {MODE_ICON[a.execution_mode ?? ""] ?? (
                  <CheckCircle size={12} className="text-gray-400" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-dark truncate">
                    {a.title}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-gray-400">
                    {formatTime(a.created_at)}
                  </span>
                  {badge && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${badge.className}`}
                    >
                      {badge.label}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
